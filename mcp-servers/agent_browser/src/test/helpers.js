/**
 * helpers.js - Shared fixtures for the agent_browser node:test suites.
 *
 * Nothing here launches Chromium: the stubs model the small slice of the
 * Playwright and CDP surfaces that the server uses, and fail loudly on any
 * CDP method they do not know (as real Chromium does).
 */

const { EventEmitter } = require('node:events');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const SERVER_ENTRY = path.join(__dirname, '..', 'index.js');

/** Point the session manager at a throwaway state root before src/ is required. */
function isolateState(prefix = 'ae-browser-test-') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  process.env.AGENT_ENHANCEMENTS_STATE_DIR = root;
  return root;
}

const DEFAULT_CDP_METHODS = new Set([
  'Page.enable', 'Runtime.enable', 'DOM.enable', 'Network.enable', 'Console.enable',
  'Log.enable', 'Overlay.enable', 'Accessibility.enable', 'CSS.enable', 'DOMSnapshot.enable',
  'Page.addScriptToEvaluateOnNewDocument', 'Page.setLifecycleEventsEnabled',
  'Emulation.setDeviceMetricsOverride', 'Emulation.setUserAgentOverride',
  'Emulation.setTimezoneOverride', 'Emulation.setHardwareConcurrencyOverride',
  'Emulation.setTouchEmulationEnabled', 'Network.setExtraHTTPHeaders'
]);

/**
 * A CDP session stub. `overrides` maps method -> (params, cdp) => result.
 * Unknown methods reject with the same message shape Chromium uses.
 */
function createStubCDP(overrides = {}, { frameId = 'FRAME_MAIN' } = {}) {
  const cdp = new EventEmitter();
  cdp.calls = [];
  cdp.detached = false;
  cdp.send = async (method, params = {}) => {
    cdp.calls.push({ method, params });
    if (Object.prototype.hasOwnProperty.call(overrides, method)) {
      return overrides[method](params, cdp);
    }
    if (method === 'Page.getFrameTree') {
      return { frameTree: { frame: { id: frameId, loaderId: 'LOADER_0', url: 'about:blank' } } };
    }
    if (method === 'Runtime.evaluate') return { result: { type: 'undefined' } };
    if (DEFAULT_CDP_METHODS.has(method)) return {};
    throw new Error(`Protocol error (${method}): '${method}' wasn't found`);
  };
  cdp.detach = async () => { cdp.detached = true; };
  return cdp;
}

function createStubPage(url = 'about:blank') {
  const page = new EventEmitter();
  page.closed = false;
  page.url = () => url;
  page.title = async () => 'Stub title';
  page.isClosed = () => page.closed;
  page.bringToFront = async () => {};
  page.close = async () => { page.closed = true; page.emit('close', page); };
  page.goto = async () => null;
  return page;
}

/** A Playwright BrowserContext stub that hands out `cdpFactory()` sessions. */
function createStubContext({ cdpFactory = () => createStubCDP(), pages } = {}) {
  const context = new EventEmitter();
  context.pageList = pages || [createStubPage()];
  context.cdpSessions = [];
  context.closed = false;
  context.initScripts = [];
  context.pages = () => context.pageList.filter((p) => !p.closed);
  context.newPage = async () => {
    const page = createStubPage();
    context.pageList.push(page);
    return page;
  };
  context.newCDPSession = async () => {
    const cdp = cdpFactory();
    context.cdpSessions.push(cdp);
    return cdp;
  };
  context.addInitScript = async (script) => { context.initScripts.push(script); };
  context.close = async () => {
    if (context.closed) return;
    context.closed = true;
    context.emit('close', context);
  };
  return context;
}

/**
 * Spawn the stdio server and expose helpers to exchange newline-delimited
 * JSON-RPC frames. Every stdout line is recorded raw so tests can assert that
 * nothing but JSON ever reaches the protocol channel.
 */
function spawnStdioServer(env = {}) {
  const child = spawn(process.execPath, [SERVER_ENTRY], {
    env: { ...process.env, ...env },
    stdio: ['pipe', 'pipe', 'pipe']
  });
  const lines = [];
  const waiters = [];
  let buffer = '';
  let stderr = '';
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (chunk) => {
    buffer += chunk;
    let index;
    while ((index = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, index);
      buffer = buffer.slice(index + 1);
      lines.push(line);
      for (const waiter of [...waiters]) waiter();
    }
  });
  child.stderr.setEncoding('utf8');
  child.stderr.on('data', (chunk) => { stderr += chunk; });
  const exited = new Promise((resolve) => child.on('exit', (code, signal) => resolve({ code, signal })));

  function parsed() {
    return lines.map((line) => JSON.parse(line));
  }

  function waitFor(predicate, timeoutMs = 5000) {
    return new Promise((resolve, reject) => {
      const check = () => {
        let messages;
        try { messages = parsed(); } catch (error) { cleanup(); reject(error); return; }
        const found = messages.find(predicate);
        if (found) { cleanup(); resolve(found); }
      };
      const timer = setTimeout(() => {
        cleanup();
        reject(new Error(`Timed out; stdout so far: ${JSON.stringify(lines)}; stderr: ${stderr.slice(-2000)}`));
      }, timeoutMs);
      function cleanup() {
        clearTimeout(timer);
        const position = waiters.indexOf(check);
        if (position !== -1) waiters.splice(position, 1);
      }
      waiters.push(check);
      check();
    });
  }

  return {
    child,
    lines,
    parsed,
    exited,
    get stderr() { return stderr; },
    write(raw) { child.stdin.write(raw); },
    send(message) { child.stdin.write(JSON.stringify(message) + '\n'); },
    waitForId(id, timeoutMs) { return waitFor((m) => m.id === id, timeoutMs); },
    waitFor,
    async close() {
      child.stdin.end();
      const timer = setTimeout(() => child.kill('SIGKILL'), 5000);
      const result = await exited;
      clearTimeout(timer);
      return result;
    }
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Decode the JSON payload of a successful tools/call result. */
function toolPayload(response) {
  const text = response.result.content[0].text;
  return JSON.parse(text);
}

module.exports = {
  SERVER_ENTRY,
  isolateState,
  createStubCDP,
  createStubPage,
  createStubContext,
  spawnStdioServer,
  sleep,
  toolPayload
};
