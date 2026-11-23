/**
 * JSON-RPC 2.0 / MCP framing over the stdio transport (no Chromium needed).
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const { spawnStdioServer, toolPayload } = require('./helpers');

function stateEnv() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ae-browser-stdio-'));
  return { root, env: { AGENT_ENHANCEMENTS_STATE_DIR: root } };
}

test('initialize, notifications and tools/list follow JSON-RPC 2.0', async () => {
  const { root, env } = stateEnv();
  const server = spawnStdioServer(env);
  try {
    server.send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: {
      protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'test', version: '0' }
    } });
    const init = await server.waitForId(1);
    assert.equal(init.jsonrpc, '2.0');
    assert.ok(init.result, 'initialize reply carries a result member');
    assert.equal(init.error, undefined);
    assert.equal(init.result.protocolVersion, '2024-11-05');
    assert.ok(init.result.capabilities.tools);
    assert.equal(init.result.serverInfo.name, 'agent_browser');
    assert.equal(init.protocolVersion, undefined, 'result fields are not spread at top level');

    server.send({ jsonrpc: '2.0', method: 'notifications/initialized' });
    server.send({ jsonrpc: '2.0', id: 2, method: 'tools/list' });
    const list = await server.waitForId(2);
    assert.ok(Array.isArray(list.result.tools));
    assert.ok(list.result.tools.length > 0);
    for (const tool of list.result.tools) {
      assert.equal(typeof tool.name, 'string');
      assert.equal(tool.inputSchema.type, 'object');
    }

    server.send({ jsonrpc: '2.0', id: 3, method: 'no/such/method' });
    const unknown = await server.waitForId(3);
    assert.equal(unknown.error.code, -32601);
    assert.equal(unknown.result, undefined);

    server.send({ jsonrpc: '2.0', id: 4, method: 'ping' });
    const ping = await server.waitForId(4);
    assert.deepEqual(ping.result, {});

    // Exactly one reply per request: the notification produced none.
    const replies = server.parsed();
    assert.deepEqual(replies.map((m) => m.id), [1, 2, 3, 4]);
  } finally {
    await server.close();
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('frames split across writes are reassembled and malformed lines get -32700', async () => {
  const { root, env } = stateEnv();
  const server = spawnStdioServer(env);
  try {
    const frame = JSON.stringify({ jsonrpc: '2.0', id: 'split', method: 'ping' });
    server.write(frame.slice(0, 10));
    await new Promise((resolve) => setTimeout(resolve, 100));
    server.write(frame.slice(10) + '\r\n');
    const pong = await server.waitForId('split');
    assert.deepEqual(pong.result, {});

    server.write('{not json}\n' + JSON.stringify({ jsonrpc: '2.0', id: 7, method: 'ping' }) + '\n');
    const parseError = await server.waitFor((m) => m.error && m.error.code === -32700);
    assert.equal(parseError.id, null);
    const after = await server.waitForId(7);
    assert.deepEqual(after.result, {}, 'a bad line does not drop the frames after it');

    server.send({ jsonrpc: '2.0', id: 8 });
    const invalid = await server.waitForId(8);
    assert.equal(invalid.error.code, -32600);
  } finally {
    await server.close();
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('tools/call validates params and reports tool failures as isError results', async () => {
  const { root, env } = stateEnv();
  const server = spawnStdioServer(env);
  try {
    server.send({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'no_such_tool', arguments: {} } });
    assert.equal((await server.waitForId(1)).error.code, -32602);

    server.send({ jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'session_get' } });
    const missing = await server.waitForId(2);
    assert.equal(missing.error.code, -32602, 'missing required sessionId is invalid params, not a crash');
    assert.match(missing.error.message, /sessionId/);

    server.send({ jsonrpc: '2.0', id: 3, method: 'tools/call' });
    assert.equal((await server.waitForId(3)).error.code, -32602);

    server.send({ jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'session_get', arguments: { sessionId: 42 } } });
    assert.equal((await server.waitForId(4)).error.code, -32602, 'wrong argument type is rejected');

    server.send({ jsonrpc: '2.0', id: 5, method: 'tools/call', params: { name: 'session_get', arguments: { sessionId: 'absent' } } });
    const absent = await server.waitForId(5);
    assert.ok(absent.result, 'tool-level failure is a result');
    assert.equal(absent.result.isError, true);
  } finally {
    await server.close();
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('session lifecycle tools work without launching a browser and keep stdout pure JSON', async () => {
  const { root, env } = stateEnv();
  const server = spawnStdioServer(env);
  try {
    server.send({ jsonrpc: '2.0', id: 1, method: 'tools/call', params: { name: 'session_create', arguments: { sessionId: 'custom-id' } } });
    const created = await server.waitForId(1);
    assert.notEqual(created.result.isError, true, JSON.stringify(created));
    assert.equal(toolPayload(created).sessionId, 'custom-id');

    server.send({ jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'session_get', arguments: { sessionId: 'custom-id' } } });
    const got = await server.waitForId(2);
    assert.notEqual(got.result.isError, true, JSON.stringify(got));
    assert.equal(toolPayload(got).session.status, 'created');

    server.send({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'session_list', arguments: {} } });
    assert.equal(toolPayload(await server.waitForId(3)).count, 1);

    server.send({ jsonrpc: '2.0', id: 4, method: 'tools/call', params: { name: 'session_delete', arguments: { sessionId: 'custom-id' } } });
    const deleted = await server.waitForId(4);
    assert.notEqual(deleted.result.isError, true, JSON.stringify(deleted));
    assert.equal(fs.existsSync(path.join(root, 'cache', 'browser', 'profiles', 'custom-id')), false);

    server.send({ jsonrpc: '2.0', id: 5, method: 'tools/call', params: { name: 'persona_list_modes', arguments: {} } });
    assert.equal(toolPayload(await server.waitForId(5)).success, true);

    for (const line of server.lines) {
      assert.doesNotThrow(() => JSON.parse(line), `non-JSON stdout line: ${line}`);
    }
    assert.match(server.stderr, /Created session/, 'diagnostics go to stderr');
  } finally {
    await server.close();
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('requests are answered in order and the server exits when stdin closes', async () => {
  const { root, env } = stateEnv();
  const server = spawnStdioServer(env);
  try {
    const batch = [];
    for (let id = 1; id <= 20; id += 1) {
      batch.push(JSON.stringify({ jsonrpc: '2.0', id, method: id % 2 ? 'ping' : 'tools/list' }));
    }
    server.write(batch.join('\n') + '\n');
    await server.waitForId(20);
    assert.deepEqual(server.parsed().map((m) => m.id), Array.from({ length: 20 }, (_, i) => i + 1));
  } finally {
    const { code } = await server.close();
    assert.equal(code, 0);
    fs.rmSync(root, { recursive: true, force: true });
  }
});
