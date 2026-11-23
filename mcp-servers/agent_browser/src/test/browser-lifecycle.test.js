/**
 * Session manager sharing and browser lifecycle, with Playwright's launcher
 * replaced by a stub (no Chromium needed).
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const { isolateState, createStubCDP, createStubContext } = require('./helpers');

const stateRoot = isolateState('ae-browser-life-');
const wrapper = require('../cdp-router-wrapper');
const { SessionManager } = require('../session-manager');
const { handleRequest, TOOLS } = require('../index');
const notifications = require('../notifications');

test.after(() => fs.rmSync(stateRoot, { recursive: true, force: true }));

let launches = [];

function stubLaunch({ failOn } = {}) {
  launches = [];
  wrapper.setBrowserLauncher({ launchPersistentContext: async (userDataDir, options) => {
    const context = createStubContext({
      cdpFactory: () => {
        if (failOn === 'newCDPSession') throw new Error('stub CDP failure');
        return createStubCDP();
      }
    });
    launches.push({ userDataDir, options, context });
    return context;
  } });
}

// Any launch a test did not stub fails instead of starting a real browser.
const refuseLaunch = { launchPersistentContext: async () => { throw new Error('unexpected browser launch'); } };
wrapper.setBrowserLauncher(refuseLaunch);
test.afterEach(() => { wrapper.setBrowserLauncher(refuseLaunch); });

function call(name, args) {
  return handleRequest({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name, arguments: args } });
}

function payload(response) {
  assert.ok(response.result, JSON.stringify(response));
  return JSON.parse(response.result.content[0].text);
}

test('the session tools and the browser launcher share one SessionManager', async () => {
  const shared = wrapper.getSessionManagerInstance();
  const created = await TOOLS.session_create({ sessionId: 'shared-one' }, {});
  assert.equal(created.sessionId, 'shared-one');
  assert.ok(await shared.getSession('shared-one'));
  assert.equal(require('../tools/session').getSessionManager(), shared);
});

test('session_create with a custom id does not try to launch a browser', async () => {
  stubLaunch();
  const response = await call('session_create', { sessionId: 'custom-create' });
  assert.notEqual(response.result.isError, true, JSON.stringify(response));
  assert.equal(payload(response).sessionId, 'custom-create');
  for (const name of ['session_get', 'session_snapshot']) {
    const res = await call(name, { sessionId: 'custom-create' });
    assert.notEqual(res.result.isError, true, `${name}: ${JSON.stringify(res)}`);
  }
  assert.equal(launches.length, 0, 'session_* tools never launch Chromium');
});

test('a second manager instance does not clobber sessions it did not create', async () => {
  const root = path.join(stateRoot, 'multi-manager');
  const a = new SessionManager({ profileRoot: root });
  const b = new SessionManager({ profileRoot: root });
  await a.createSession({ sessionId: 'from-a' });
  await b.createSession({ sessionId: 'from-b' });
  a.markSessionActive('from-a');
  const fresh = new SessionManager({ profileRoot: root });
  assert.ok(fresh.getSessionMetadata('from-a'));
  assert.ok(fresh.getSessionMetadata('from-b'), 'session created by the other manager survives');
  assert.ok(await a.getSession('from-b'), 'reads see sessions saved by other managers');
});

test('launch uses secure defaults and grants no permissions', async () => {
  stubLaunch();
  await TOOLS.session_create({ sessionId: 'secure-launch' }, {});
  const response = await call('get_current_url', { sessionId: 'secure-launch' });
  assert.notEqual(response.result.isError, true, JSON.stringify(response));
  assert.equal(launches.length, 1, 'browser tools auto-launch the session');
  const { options, userDataDir } = launches[0];
  assert.equal(options.permissions, undefined);
  for (const flag of ['--disable-web-security', '--ignore-certificate-errors', '--allow-running-insecure-content']) {
    assert.ok(!options.args.includes(flag), `${flag} must not be on by default`);
  }
  assert.ok(!options.args.some((a) => /site-per-process|IsolateOrigins|disable-site-isolation/.test(a)));
  assert.equal(userDataDir, (await wrapper.getSessionManagerInstance().getSession('secure-launch')).profilePath);
  await call('session_close', { sessionId: 'secure-launch' });
});

test('insecure mode is opt-in and uses a throwaway profile', async () => {
  stubLaunch();
  process.env.AGENT_BROWSER_INSECURE = '1';
  try {
    await TOOLS.session_create({ sessionId: 'insecure-launch' }, {});
    await wrapper.initializeBrowser('insecure-launch');
    const { options, userDataDir } = launches[0];
    assert.ok(options.args.includes('--disable-web-security'));
    assert.ok(options.args.includes('--ignore-certificate-errors'));
    assert.equal(userDataDir, '', 'persistent profile is not used in insecure mode');
  } finally {
    delete process.env.AGENT_BROWSER_INSECURE;
    await wrapper.closeBrowser('insecure-launch');
  }
});

test('closeBrowser tears down router state, captures and the active entry', async () => {
  stubLaunch();
  await TOOLS.session_create({ sessionId: 'close-me' }, {});
  await wrapper.initializeBrowser('close-me');
  const capture = await TOOLS.cdp_console_capture({ sessionId: 'close-me' }, {});
  assert.equal(capture.success, true);
  assert.equal((await TOOLS.cdp_capture_list({ sessionId: 'close-me' }, {})).count, 1);

  const closed = payload(await call('session_close', { sessionId: 'close-me' }));
  assert.equal(closed.success, true);
  assert.equal(wrapper.activeBrowsers.has('close-me'), false);
  assert.equal(wrapper.getCDPRouter().sessions.has('close-me'), false);
  assert.equal(launches[0].context.closed, true);
  assert.equal((await TOOLS.cdp_capture_list({ sessionId: 'close-me' }, {})).count, 0);
  assert.equal((await wrapper.getSessionManagerInstance().getSession('close-me')).status, 'closed');
});

test('a browser that exits on its own is cleaned up', async () => {
  stubLaunch();
  await TOOLS.session_create({ sessionId: 'crashes' }, {});
  await wrapper.initializeBrowser('crashes');
  await launches[0].context.close();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(wrapper.activeBrowsers.has('crashes'), false);
  assert.equal(wrapper.getCDPRouter().sessions.has('crashes'), false);
});

test('a failed initialisation closes the launched browser', async () => {
  stubLaunch({ failOn: 'newCDPSession' });
  await TOOLS.session_create({ sessionId: 'fails-init' }, {});
  await assert.rejects(wrapper.initializeBrowser('fails-init'), /stub CDP failure/);
  assert.equal(launches[0].context.closed, true);
  assert.equal(wrapper.activeBrowsers.has('fails-init'), false);
  assert.equal(wrapper.getCDPRouter().sessions.has('fails-init'), false);
});

test('session_delete closes an active browser before removing its profile', async () => {
  stubLaunch();
  const { profilePath } = await TOOLS.session_create({ sessionId: 'delete-active' }, {});
  await wrapper.initializeBrowser('delete-active');
  const response = await call('session_delete', { sessionId: 'delete-active' });
  assert.notEqual(response.result.isError, true, JSON.stringify(response));
  assert.equal(launches[0].context.closed, true);
  assert.equal(wrapper.activeBrowsers.has('delete-active'), false);
  assert.equal(fs.existsSync(profilePath), false);
});

test('cdp_subscribe forwards events as MCP notifications and cdp_unsubscribe stops them', async () => {
  stubLaunch();
  await TOOLS.session_create({ sessionId: 'events' }, {});
  await wrapper.initializeBrowser('events');
  const received = [];
  const listener = (n) => received.push(n);
  notifications.notificationManager.on('notification', listener);
  try {
    const sub = await TOOLS.cdp_subscribe({ sessionId: 'events', domain: 'Page', event: 'loadEventFired' }, {});
    const cdp = await wrapper.getCDPRouter().getPageCDP('events');
    cdp.emit('Page.loadEventFired', { timestamp: 5 });
    assert.equal(received.length, 1);
    assert.equal(received[0].method, 'notifications/cdp_event');
    assert.equal(received[0].params.data.timestamp, 5);
    const unsub = await TOOLS.cdp_unsubscribe({ sessionId: 'events', subscriptionId: sub.subscriptionId }, {});
    assert.equal(unsub.success, true);
    cdp.emit('Page.loadEventFired', { timestamp: 6 });
    assert.equal(received.length, 1);
  } finally {
    notifications.notificationManager.off('notification', listener);
    await wrapper.closeBrowser('events');
  }
});

test('network capture can be read and stopped', async () => {
  stubLaunch();
  await TOOLS.session_create({ sessionId: 'net' }, {});
  await wrapper.initializeBrowser('net');
  try {
    const { captureId } = await TOOLS.cdp_network_capture({ sessionId: 'net', includeBody: false }, {});
    const cdp = await wrapper.getCDPRouter().getPageCDP('net');
    cdp.emit('Network.requestWillBeSent', { requestId: 'r1', request: { url: 'https://a.test/', method: 'GET', headers: {} }, timestamp: 1 });
    assert.equal((await TOOLS.cdp_capture_get({ captureId }, {})).count, 1);
    const stopped = await TOOLS.cdp_capture_stop({ captureId }, {});
    assert.equal(stopped.count, 1);
    assert.equal(cdp.listenerCount('Network.requestWillBeSent'), 0);
  } finally {
    await wrapper.closeBrowser('net');
  }
});
