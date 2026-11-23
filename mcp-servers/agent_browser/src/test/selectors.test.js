/**
 * Selectors and XPaths reach the page exactly as written.
 *
 * The CDP stub captures every Runtime.evaluate expression; each one is then
 * evaluated in a vm sandbox whose fake `document` records what it was asked
 * for. Before the fix, backslashes and quotes changed the string or broke out
 * of the literal.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');

const { isolateState, createStubCDP, createStubContext } = require('./helpers');

const stateRoot = isolateState('ae-browser-sel-');
const wrapper = require('../cdp-router-wrapper');
const { TOOLS } = require('../index');

test.after(() => fs.rmSync(stateRoot, { recursive: true, force: true }));

const TRICKY = ['#id\\:x', "a\\'", "a[title='it\\'s']", 'a"b', 'x\\', "'); globalThis.pwned = 1; ('"];
const TRICKY_XPATH = ["//a[@title=\"it's\"]", "//a[text()='\\']", '//*[contains(., "\\u2028")]'];

let counter = 0;
function stubSession() {
  const sessionId = `sel-${++counter}`;
  const expressions = [];
  const context = createStubContext({
    cdpFactory: () => createStubCDP({
      'Runtime.evaluate': (params) => {
        expressions.push(params.expression);
        return { result: { type: 'object', subtype: 'null' } };
      }
    })
  });
  wrapper.getCDPRouter().registerSession(sessionId, {
    browser: context, context, defaultPage: context.pageList[0], emulationConfig: null
  });
  return { sessionId, expressions };
}

/** Evaluate each captured expression and return the strings the DOM saw. */
function replay(expressions) {
  const seen = [];
  const sandbox = {
    document: {
      querySelector: (s) => { seen.push(s); return null; },
      querySelectorAll: (s) => { seen.push(s); return []; },
      evaluate: (x) => { seen.push(x); return { singleNodeValue: null, snapshotLength: 0 }; },
      documentElement: {}
    },
    XPathResult: { FIRST_ORDERED_NODE_TYPE: 9, ORDERED_NODE_SNAPSHOT_TYPE: 7 }
  };
  vm.createContext(sandbox);
  for (const expression of expressions) {
    if (!/querySelector|evaluate\(/.test(expression)) continue;
    vm.runInContext(expression, sandbox);
  }
  assert.equal(sandbox.pwned, undefined, 'selector text never executes as code');
  return seen;
}

const SELECTOR_TOOLS = {
  click: (selector) => ({ selector, humanize: false }),
  get_attributes: (selector) => ({ selector }),
  extract: (selector) => ({ selector }),
  screenshot: (selector) => ({ selector })
};

for (const [tool, build] of Object.entries(SELECTOR_TOOLS)) {
  test(`${tool} passes CSS selectors through unchanged`, async () => {
    for (const selector of TRICKY) {
      const { sessionId, expressions } = stubSession();
      try { await TOOLS[tool]({ sessionId, ...build(selector) }, {}); } catch (error) {
        assert.ok(!(error instanceof TypeError), error.stack);
      }
      assert.deepEqual(replay(expressions), [selector]);
    }
  });
}

for (const tool of ['click', 'get_attributes', 'extract', 'screenshot']) {
  test(`${tool} passes XPath expressions through unchanged`, async () => {
    for (const xpath of TRICKY_XPATH) {
      const { sessionId, expressions } = stubSession();
      try { await TOOLS[tool]({ sessionId, xpath, humanize: false }, {}); } catch (error) {
        assert.ok(!(error instanceof TypeError), error.stack);
      }
      assert.deepEqual(replay(expressions), [xpath]);
    }
  });
}

test('extract with multiple=true keeps the selector intact', async () => {
  const { sessionId, expressions } = stubSession();
  await TOOLS.extract({ sessionId, selector: TRICKY[1], multiple: true }, {});
  assert.deepEqual(replay(expressions), [TRICKY[1]]);
});
