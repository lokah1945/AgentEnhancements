/**
 * navigate / history / reload wait logic against a scripted CDP stub.
 */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');

const { isolateState, createStubCDP, createStubContext } = require('./helpers');

const stateRoot = isolateState('ae-browser-nav-');
const wrapper = require('../cdp-router-wrapper');
const navigation = require('../tools/navigation');

test.after(() => fs.rmSync(stateRoot, { recursive: true, force: true }));

let counter = 0;

/**
 * Register a stub session whose CDP emits lifecycle events for each
 * navigation. `when` controls whether events fire before Page.navigate
 * resolves ('sync') or afterwards ('async').
 */
function stubSession({ when = 'async', events = ['DOMContentLoaded', 'load', 'networkIdle'], navigateResult, history } = {}) {
  const sessionId = `nav-${++counter}`;
  let loader = 0;
  const emitLifecycle = (cdp, loaderId) => {
    const fire = () => {
      for (const name of events) cdp.emit('Page.lifecycleEvent', { frameId: 'FRAME_MAIN', loaderId, name, timestamp: 1 });
    };
    if (when === 'sync') fire(); else setImmediate(fire);
  };
  const commit = (cdp, loaderId) => {
    cdp.emit('Page.frameNavigated', { frame: { id: 'FRAME_MAIN', loaderId, url: 'https://example.test/' }, type: 'Navigation' });
    emitLifecycle(cdp, loaderId);
  };
  let cdp;
  const context = createStubContext({
    cdpFactory: () => {
      cdp = createStubCDP({
        'Page.navigate': (params, self) => {
          if (navigateResult) return navigateResult;
          const loaderId = `L${++loader}`;
          // Lifecycle of the *previous* document must not satisfy the wait.
          self.emit('Page.lifecycleEvent', { frameId: 'FRAME_MAIN', loaderId: 'L_OLD', name: 'load' });
          commit(self, loaderId);
          return { frameId: 'FRAME_MAIN', loaderId };
        },
        'Page.reload': (params, self) => { setImmediate(() => commit(self, `R${++loader}`)); return {}; },
        'Page.getNavigationHistory': () => history || { currentIndex: 1, entries: [{ id: 10, url: 'a' }, { id: 11, url: 'b' }, { id: 12, url: 'c' }] },
        'Page.navigateToHistoryEntry': (params, self) => {
          self.lastHistoryEntry = params.entryId;
          setImmediate(() => commit(self, `H${++loader}`));
          return {};
        },
        'Runtime.evaluate': () => ({ result: { value: { title: 'Example', url: 'https://example.test/', readyState: 'complete' } } })
      });
      return cdp;
    }
  });
  wrapper.getCDPRouter().registerSession(sessionId, {
    browser: context, context, defaultPage: context.pageList[0], emulationConfig: null
  });
  return { sessionId, getCdp: () => cdp };
}

test('navigate waits for DOMContentLoaded of the new document by default', async () => {
  const { sessionId, getCdp } = stubSession();
  const result = await navigation.navigate({ sessionId, url: 'https://example.test/' }, {});
  assert.equal(result.success, true);
  assert.equal(result.title, 'Example');
  const methods = getCdp().calls.map((c) => c.method);
  assert.ok(!methods.includes('Page.domContentLoaded'), 'never sends an event name as a command');
  assert.equal(getCdp().listenerCount('Page.lifecycleEvent'), 0, 'listeners are removed');
});

for (const waitUntil of ['load', 'networkIdle']) {
  test(`navigate waitUntil=${waitUntil} catches events that fire before Page.navigate resolves`, async () => {
    const { sessionId, getCdp } = stubSession({ when: 'sync' });
    const result = await navigation.navigate({ sessionId, url: 'https://example.test/', waitUntil, timeout: 2000 }, {});
    assert.equal(result.success, true);
    assert.equal(getCdp().listenerCount('Page.lifecycleEvent'), 0);
  });
}

test('navigate surfaces Page.navigate errorText', async () => {
  const { sessionId } = stubSession({ navigateResult: { frameId: 'FRAME_MAIN', loaderId: 'L9', errorText: 'net::ERR_NAME_NOT_RESOLVED' } });
  await assert.rejects(
    navigation.navigate({ sessionId, url: 'https://nx.invalid/' }, {}),
    /ERR_NAME_NOT_RESOLVED/
  );
});

test('navigate times out and cleans up when the event never arrives', async () => {
  const { sessionId, getCdp } = stubSession({ events: ['DOMContentLoaded'] });
  await assert.rejects(
    navigation.navigate({ sessionId, url: 'https://example.test/', waitUntil: 'networkIdle', timeout: 100 }, {}),
    /Timed out/
  );
  assert.equal(getCdp().listenerCount('Page.lifecycleEvent'), 0);
  assert.equal(getCdp().listenerCount('Page.frameNavigated'), 0);
});

test('same-document navigations resolve without waiting for load', async () => {
  const { sessionId } = stubSession({ navigateResult: { frameId: 'FRAME_MAIN' }, events: [] });
  const result = await navigation.navigate({ sessionId, url: 'https://example.test/#anchor', timeout: 200 }, {});
  assert.equal(result.success, true);
});

test('referrer is passed to Page.navigate instead of a sticky header', async () => {
  const { sessionId, getCdp } = stubSession();
  await navigation.navigate({ sessionId, url: 'https://example.test/', referrer: 'https://ref.example/' }, {});
  const nav = getCdp().calls.find((c) => c.method === 'Page.navigate');
  assert.equal(nav.params.referrer, 'https://ref.example/');
  assert.ok(!getCdp().calls.some((c) => c.method === 'Network.setExtraHTTPHeaders'));
});

test('go_back and go_forward use the navigation history', async () => {
  const { sessionId, getCdp } = stubSession();
  assert.equal((await navigation.goBack({ sessionId }, {})).success, true);
  assert.equal(getCdp().lastHistoryEntry, 10);
  assert.equal((await navigation.goForward({ sessionId }, {})).success, true);
  assert.equal(getCdp().lastHistoryEntry, 12);
});

test('go_back at the start of history reports that nothing happened', async () => {
  const { sessionId } = stubSession({ history: { currentIndex: 0, entries: [{ id: 1, url: 'a' }] } });
  const result = await navigation.goBack({ sessionId }, {});
  assert.equal(result.success, false);
});

test('reload waits for the reloaded document', async () => {
  const { sessionId, getCdp } = stubSession();
  assert.equal((await navigation.reload({ sessionId, ignoreCache: true }, {})).success, true);
  assert.deepEqual(getCdp().calls.find((c) => c.method === 'Page.reload').params, { ignoreCache: true });
});
