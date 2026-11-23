/**
 * CDPRouter page bookkeeping with stubbed Playwright objects.
 */

const assert = require('node:assert/strict');
const test = require('node:test');

const { CDPRouter } = require('../cdp-router');
const { createStubCDP, createStubContext, createStubPage } = require('./helpers');

function setup(options) {
  const router = new CDPRouter();
  const context = createStubContext(options);
  const page = context.pageList[0];
  router.registerSession('s1', { browser: context, context, defaultPage: page, emulationConfig: null });
  return { router, context, page };
}

test("getPageCDP('default') reuses one CDP session per page", async () => {
  const { router, context } = setup();
  const first = await router.getPageCDP('s1', 'default');
  const second = await router.getPageCDP('s1', 'default');
  assert.equal(first, second);
  assert.equal(context.cdpSessions.length, 1, 'newCDPSession is called once');
  const scripts = first.calls.filter((c) => c.method === 'Page.addScriptToEvaluateOnNewDocument');
  assert.equal(scripts.length, 1, 'init scripts are not re-added on every call');
  const session = router.getSession('s1');
  assert.equal(session.pages.size, 1, 'no phantom page entries');
  const [entry] = session.pages.values();
  assert.equal(entry.frameId, 'FRAME_MAIN', 'main frame id comes from Page.getFrameTree');
});

test('concurrent lookups share one CDP session', async () => {
  const { router, context } = setup();
  const [a, b] = await Promise.all([router.getPageCDP('s1'), router.getPageCDP('s1')]);
  assert.equal(a, b);
  assert.equal(context.cdpSessions.length, 1);
});

test('page ids are stable and listed pages resolve their titles', async () => {
  const { router, page } = setup();
  await router.getPageCDP('s1', 'default');
  const id = router.getPageId(page);
  assert.equal(router.getPageId(page), id);
  const pages = await router.getPages('s1');
  assert.equal(pages.length, 1);
  assert.equal(pages[0].pageId, id);
  assert.equal(pages[0].title, 'Stub title');
  assert.equal(await router.getPageCDP('s1', id), await router.getPageCDP('s1', 'default'));
});

test('new tabs get their own CDP session and can become the active page', async () => {
  const { router, context } = setup();
  const defaultCdp = await router.getPageCDP('s1');
  const { pageId, cdp } = await router.createPage('s1');
  assert.notEqual(cdp, defaultCdp);
  assert.equal((await router.getPages('s1')).length, 2);
  await router.bringToFront('s1', pageId);
  assert.equal(await router.getPageCDP('s1', 'default'), cdp, "'default' follows the active tab");
  await router.closePage('s1', pageId);
  assert.equal(cdp.detached, true);
  assert.equal(await router.getPageCDP('s1', 'default'), defaultCdp, 'falls back to a remaining page');
  assert.equal(context.cdpSessions.length, 2);
});

test('a page closed by the browser is dropped from the index', async () => {
  const { router, context } = setup();
  const extra = createStubPage('https://popup.example/');
  context.pageList.push(extra);
  const id = router.getPageId(extra);
  const cdp = await router.getPageCDP('s1', id);
  await extra.close();
  assert.equal(router.getSession('s1').pages.has(id), false);
  assert.equal(cdp.detached, true);
  await assert.rejects(router.getPageCDP('s1', id), /Page not found/);
});

test('closeSession detaches CDP sessions and forgets the session', async () => {
  const { router, context } = setup();
  const cdp = await router.getPageCDP('s1');
  await router.closeSession('s1');
  assert.equal(cdp.detached, true);
  assert.equal(context.closed, true);
  assert.equal(router.sessions.has('s1'), false);
});

test('frame-targeted evaluate uses the CDP session that owns the frame', async () => {
  const router = new CDPRouter();
  const context = createStubContext({
    cdpFactory: () => createStubCDP({ 'Runtime.evaluate': () => ({ result: { value: 'from-frame' } }) })
  });
  router.registerSession('s1', { browser: context, context, defaultPage: context.pageList[0] });
  assert.equal(await router.evaluate('s1', '1', { target: 'frame', frameId: 'FRAME_MAIN' }), 'from-frame');
});
