/**
 * Chromium launch flags keep the browser's security model intact by default.
 */

const assert = require('node:assert/strict');
const test = require('node:test');

const { buildLaunchArgs, isInsecureMode } = require('../launch-config');

const INSECURE_FLAGS = [
  '--disable-web-security',
  '--disable-site-isolation-trials',
  '--allow-running-insecure-content',
  '--ignore-certificate-errors',
  '--ignore-ssl-errors',
  '--allow-insecure-localhost'
];

test('default launch arguments keep SOP, site isolation and TLS validation on', () => {
  const args = buildLaunchArgs({});
  for (const flag of INSECURE_FLAGS) {
    assert.ok(!args.includes(flag), `${flag} present by default`);
  }
  assert.ok(!args.some((a) => a.startsWith('--ignore-certificate-errors')));
  assert.ok(!args.some((a) => /IsolateOrigins|site-per-process/.test(a)), 'site isolation stays enabled');
});

test('relaxed flags are only added when explicitly requested', () => {
  const args = buildLaunchArgs({ insecure: true });
  for (const flag of ['--disable-web-security', '--ignore-certificate-errors', '--disable-site-isolation-trials']) {
    assert.ok(args.includes(flag), `${flag} missing in insecure mode`);
  }
});

test('the insecure opt-in only accepts explicit truthy values', () => {
  assert.equal(isInsecureMode({}), false);
  assert.equal(isInsecureMode({ AGENT_BROWSER_INSECURE: '' }), false);
  assert.equal(isInsecureMode({ AGENT_BROWSER_INSECURE: '0' }), false);
  assert.equal(isInsecureMode({ AGENT_BROWSER_INSECURE: 'false' }), false);
  assert.equal(isInsecureMode({ AGENT_BROWSER_INSECURE: '1' }), true);
  assert.equal(isInsecureMode({ AGENT_BROWSER_INSECURE: 'true' }), true);
});

test('proxy and locale arguments are still honoured', () => {
  const args = buildLaunchArgs({ locale: 'de-DE', proxy: { server: 'http://127.0.0.1:8080', bypass: 'localhost' } });
  assert.ok(args.includes('--lang=de-DE'));
  assert.ok(args.includes('--proxy-server=http://127.0.0.1:8080'));
  assert.ok(args.includes('--proxy-bypass-list=localhost'));
});
