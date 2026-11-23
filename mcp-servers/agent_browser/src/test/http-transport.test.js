/**
 * Streamable-HTTP-style transport hardening (no Chromium needed).
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const test = require('node:test');

const { isolateState } = require('./helpers');

const stateRoot = isolateState('ae-browser-http-');
const { startHttpServer } = require('../index');

test.after(() => fs.rmSync(stateRoot, { recursive: true, force: true }));

function request(server, { method = 'POST', path = '/mcp', headers = {}, body } = {}) {
  const { port } = server.address();
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, method, path, headers }, (res) => {
      let data = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
    if (body !== undefined) req.write(body);
    req.end();
  });
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };
const PING = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'ping' });

async function withServer(options, fn) {
  const server = await startHttpServer({ port: 0, ...options });
  try {
    await fn(server);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test('binds to loopback by default and answers JSON-RPC with a result member', async () => {
  await withServer({}, async (server) => {
    assert.equal(server.address().address, '127.0.0.1');
    const res = await request(server, { headers: JSON_HEADERS, body: PING });
    assert.equal(res.status, 200);
    const payload = JSON.parse(res.body);
    assert.deepEqual(payload, { jsonrpc: '2.0', id: 1, result: {} });
    assert.equal(res.headers['access-control-allow-origin'], undefined);
  });
});

test('notifications get 202 with no JSON-RPC body', async () => {
  await withServer({}, async (server) => {
    const res = await request(server, {
      headers: JSON_HEADERS,
      body: JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' })
    });
    assert.equal(res.status, 202);
    assert.equal(res.body, '');
  });
});

test('rejects non-JSON content types (no CORS-simple requests)', async () => {
  await withServer({}, async (server) => {
    const res = await request(server, { headers: { 'Content-Type': 'text/plain' }, body: PING });
    assert.equal(res.status, 415);
  });
});

test('rejects cross-origin and DNS-rebinding requests', async () => {
  await withServer({}, async (server) => {
    const evilOrigin = await request(server, {
      headers: { ...JSON_HEADERS, Origin: 'https://evil.example' }, body: PING
    });
    assert.equal(evilOrigin.status, 403);

    const rebinding = await request(server, {
      headers: { ...JSON_HEADERS, Host: 'evil.example:80' }, body: PING
    });
    assert.equal(rebinding.status, 403);

    const local = await request(server, {
      headers: { ...JSON_HEADERS, Origin: `http://localhost:${server.address().port}` }, body: PING
    });
    assert.equal(local.status, 200);
  });
});

test('caps the request body size', async () => {
  await withServer({ maxBodyBytes: 1024 }, async (server) => {
    const big = JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'ping', params: { pad: 'x'.repeat(4096) } });
    const res = await request(server, { headers: JSON_HEADERS, body: big });
    assert.equal(res.status, 413);
  });
});

test('enforces the optional bearer token', async () => {
  await withServer({ token: 'test-token-123' }, async (server) => {
    const missing = await request(server, { headers: JSON_HEADERS, body: PING });
    assert.equal(missing.status, 401);
    const wrong = await request(server, { headers: { ...JSON_HEADERS, Authorization: 'Bearer nope' }, body: PING });
    assert.equal(wrong.status, 401);
    const ok = await request(server, {
      headers: { ...JSON_HEADERS, Authorization: 'Bearer test-token-123' }, body: PING
    });
    assert.equal(ok.status, 200);
    assert.deepEqual(JSON.parse(ok.body).result, {});
  });
});

test('refuses a non-loopback bind without a token', async () => {
  await assert.rejects(startHttpServer({ port: 0, host: '0.0.0.0' }), /token/i);
});

test('parse errors and wrong methods are rejected cleanly', async () => {
  await withServer({}, async (server) => {
    const bad = await request(server, { headers: JSON_HEADERS, body: '{oops' });
    assert.equal(bad.status, 400);
    assert.equal(JSON.parse(bad.body).error.code, -32700);
    const get = await request(server, { method: 'GET' });
    assert.equal(get.status, 405);
    const health = await request(server, { method: 'GET', path: '/health' });
    assert.equal(health.status, 200);
  });
});
