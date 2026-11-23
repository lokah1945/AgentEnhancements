/**
 * End-to-end over stdio with a real Chromium. Opt-in: AGENT_BROWSER_E2E=1
 * (needs the Playwright Chromium build, e.g. `npx playwright install chromium`).
 * Only a loopback HTTP server started by the test is visited.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { spawnStdioServer, toolPayload } = require('./helpers');

const enabled = process.env.AGENT_BROWSER_E2E === '1';

test('stdio session drives a real browser end to end', { skip: !enabled && 'set AGENT_BROWSER_E2E=1 to run', timeout: 120000 }, async () => {
  const site = http.createServer((req, res) => {
    if (req.url === '/slow.js') {
      setTimeout(() => { res.writeHead(200, { 'Content-Type': 'text/javascript' }); res.end('window.slow = 1;'); }, 300);
      return;
    }
    const title = req.url === '/second' ? 'Second' : 'First';
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`<!doctype html><title>${title}</title><body><p id="a:b" title="it's">Hello ${title}</p>` +
      '<a href="/second">next</a><script src="/slow.js"></script></body>');
  });
  await new Promise((resolve) => site.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${site.address().port}`;
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ae-browser-e2e-'));
  const server = spawnStdioServer({ AGENT_ENHANCEMENTS_STATE_DIR: root });
  let id = 0;
  async function call(name, args, timeoutMs = 60000) {
    id += 1;
    server.send({ jsonrpc: '2.0', id, method: 'tools/call', params: { name, arguments: args } });
    const response = await server.waitForId(id, timeoutMs);
    assert.ok(response.result, JSON.stringify(response));
    assert.notEqual(response.result.isError, true, `${name}: ${response.result.content[0].text}`);
    return toolPayload(response);
  }
  try {
    server.send({ jsonrpc: '2.0', id: 'init', method: 'initialize', params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'e2e', version: '0' } } });
    await server.waitForId('init');
    server.send({ jsonrpc: '2.0', method: 'notifications/initialized' });

    await call('session_create', { sessionId: 'e2e' });
    const first = await call('navigate', { sessionId: 'e2e', url: `${base}/`, waitUntil: 'load' });
    assert.equal(first.title, 'First');
    const second = await call('navigate', { sessionId: 'e2e', url: `${base}/second`, waitUntil: 'networkIdle' });
    assert.equal(second.title, 'Second');
    const back = await call('go_back', { sessionId: 'e2e' });
    assert.equal(back.success, true);
    assert.equal((await call('get_current_url', { sessionId: 'e2e' })).url, `${base}/`);
    assert.equal((await call('reload', { sessionId: 'e2e' })).success, true);

    const attrs = await call('get_attributes', { sessionId: 'e2e', selector: '#a\\:b', attributes: ['title'] });
    assert.equal(attrs.attributes.title, "it's");
    const text = await call('extract', { sessionId: 'e2e', xpath: "//p[@title=\"it's\"]" });
    assert.equal(text.data, 'Hello First');
    assert.equal((await call('cdp_evaluate', { sessionId: 'e2e', expression: '6 * 7' })).value, 42);

    const tabs = await call('tab_list', { sessionId: 'e2e' });
    assert.equal(tabs.count, 1);
    assert.equal(tabs.tabs[0].title, 'First');
    const opened = await call('tab_new', { sessionId: 'e2e', url: `${base}/second` });
    assert.equal((await call('get_current_url', { sessionId: 'e2e' })).url, `${base}/second`);
    assert.equal((await call('tab_list', { sessionId: 'e2e' })).count, 2);
    await call('tab_close', { sessionId: 'e2e', tabId: opened.pageId });
    assert.equal((await call('tab_list', { sessionId: 'e2e' })).count, 1);

    const shot = await call('screenshot', { sessionId: 'e2e' });
    assert.ok(Buffer.from(shot.data, 'base64').subarray(1, 4).toString() === 'PNG');
    assert.ok(Array.isArray((await call('cdp_metrics', { sessionId: 'e2e' })).metrics));

    assert.equal((await call('session_close', { sessionId: 'e2e' })).wasActive, true);
    await call('session_delete', { sessionId: 'e2e' });

    for (const line of server.lines) assert.doesNotThrow(() => JSON.parse(line), line);
  } finally {
    await server.close();
    await new Promise((resolve) => site.close(resolve));
    fs.rmSync(root, { recursive: true, force: true });
  }
});
