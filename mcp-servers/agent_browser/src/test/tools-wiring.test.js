/**
 * Every advertised tool is wired to a working handler (no Chromium needed).
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const { isolateState } = require('./helpers');

const stateRoot = isolateState('ae-browser-wiring-');
const wrapper = require('../cdp-router-wrapper');
const { TOOLS, TOOL_SCHEMAS } = require('../index');

test.after(() => fs.rmSync(stateRoot, { recursive: true, force: true }));

test('every name a tool module imports from the wrapper is an exported function', () => {
  const toolsDir = path.join(__dirname, '..', 'tools');
  for (const file of fs.readdirSync(toolsDir).filter((f) => f.endsWith('.js'))) {
    const source = fs.readFileSync(path.join(toolsDir, file), 'utf8');
    const pattern = /const\s*\{([^}]+)\}\s*=\s*require\('\.\.\/cdp-router-wrapper'\)/g;
    let match;
    while ((match = pattern.exec(source)) !== null) {
      for (const name of match[1].split(',').map((s) => s.trim().split(':')[0].trim()).filter(Boolean)) {
        assert.ok(Object.prototype.hasOwnProperty.call(wrapper, name), `${file} imports missing wrapper export ${name}`);
        if (/^get[A-Z]/.test(name)) {
          assert.equal(typeof wrapper[name], 'function', `${file} imports ${name}, which is not a function`);
        }
      }
    }
  }
});

test('the advertised tool list and the handler table match exactly', () => {
  assert.deepEqual(Object.keys(TOOLS).sort(), Object.keys(TOOL_SCHEMAS).sort());
  for (const [name, handler] of Object.entries(TOOLS)) {
    assert.equal(typeof handler, 'function', `${name} has no handler`);
    assert.equal(TOOL_SCHEMAS[name].name, name);
    assert.equal(TOOL_SCHEMAS[name].inputSchema.type, 'object');
  }
});

test('the browser tools are wired: an unknown session is a clean error, not a TypeError', async () => {
  const calls = {
    navigate: { url: 'about:blank' },
    go_back: {},
    get_current_url: {},
    tab_list: {},
    click: { selector: 'a' },
    cdp_send: { domain: 'Page', method: 'enable' },
    cdp_evaluate: { expression: '1' },
    cdp_subscribe: { domain: 'Page', event: 'loadEventFired' },
    cdp_network_capture: {},
    cdp_metrics: {},
    extract: { selector: 'a' },
    screenshot: {},
    get_text: {}
  };
  for (const [name, extra] of Object.entries(calls)) {
    await assert.rejects(
      TOOLS[name]({ sessionId: 'no-such-session', ...extra }, {}),
      (error) => {
        assert.ok(!(error instanceof TypeError), `${name}: ${error.stack}`);
        assert.match(error.message, /Session not found/);
        return true;
      }
    );
  }
});

test('capture management tools work without a browser', async () => {
  assert.deepEqual(await TOOLS.cdp_capture_list({}, {}), { success: true, captures: [], count: 0 });
  assert.equal((await TOOLS.cdp_capture_get({ captureId: 'nope' }, {})).success, false);
  assert.equal((await TOOLS.cdp_capture_stop({ captureId: 'nope' }, {})).success, false);
});

test('persona tools return results instead of throwing', async () => {
  const unknown = await TOOLS.persona_create({ template: 'no_such_template' }, {});
  assert.equal(unknown.success, false);
  const templates = await TOOLS.persona_list_templates({}, {});
  assert.equal(templates.success, true);
  const first = templates.templates[0];
  const name = typeof first === 'string' ? first : first.name;
  const withOverrides = await TOOLS.persona_create({ template: name, overrides: { notes: 'x' } }, {});
  assert.equal(withOverrides.success, true, JSON.stringify(withOverrides));
  const set = await TOOLS.persona_set({ sessionId: 's' }, {});
  assert.equal(set.success, true);
});
