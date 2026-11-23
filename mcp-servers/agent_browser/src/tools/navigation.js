/**
 * navigation.js - Navigation MCP tools
 *
 * Every navigation registers its wait condition before the navigation is
 * started (so fast pages cannot fire their events before anyone listens),
 * matches lifecycle events to the document the navigation created, and always
 * removes its listeners, including on timeout and on error.
 */

const { getCDPRouter } = require('../cdp-router-wrapper');

const DEFAULT_TIMEOUT_MS = 30000;

/** waitUntil value -> Page.lifecycleEvent name. */
const LIFECYCLE_EVENTS = {
  domContentLoaded: 'DOMContentLoaded',
  load: 'load',
  networkIdle: 'networkIdle'
};

/**
 * Start a navigation with `trigger()` and wait until the main frame's new
 * document reaches `waitUntil`.
 *
 * `trigger` returns the CDP result; when it carries a loaderId (Page.navigate)
 * that identifies the new document, otherwise the next main-frame
 * Page.frameNavigated does. Same-document navigations and back/forward-cache
 * restores complete as soon as they commit.
 */
async function runNavigation(cdp, trigger, { waitUntil = 'domContentLoaded', timeout = DEFAULT_TIMEOUT_MS } = {}) {
  const lifecycleName = LIFECYCLE_EVENTS[waitUntil];
  if (!lifecycleName) {
    throw new Error(`Invalid waitUntil: ${waitUntil} (expected one of ${Object.keys(LIFECYCLE_EVENTS).join(', ')})`);
  }
  const timeoutMs = Number.isFinite(timeout) && timeout > 0 ? timeout : DEFAULT_TIMEOUT_MS;

  await cdp.send('Page.enable');
  await cdp.send('Page.setLifecycleEventsEnabled', { enabled: true });
  const { frameTree } = await cdp.send('Page.getFrameTree');
  const mainFrameId = frameTree.frame.id;

  const reached = new Set(); // loaderIds whose document reached lifecycleName
  let committed = null; // { loaderId, done }
  let wake = () => {};

  const onLifecycle = (event) => {
    if (event.frameId === mainFrameId && event.name === lifecycleName) {
      reached.add(event.loaderId);
      wake();
    }
  };
  const onFrameNavigated = ({ frame, type }) => {
    if (frame.parentId || frame.id !== mainFrameId || committed) return;
    committed = { loaderId: frame.loaderId, done: type === 'BackForwardCacheRestore' };
    wake();
  };
  const onSameDocument = ({ frameId }) => {
    if (frameId !== mainFrameId || committed) return;
    committed = { loaderId: null, done: true };
    wake();
  };

  cdp.on('Page.lifecycleEvent', onLifecycle);
  cdp.on('Page.frameNavigated', onFrameNavigated);
  cdp.on('Page.navigatedWithinDocument', onSameDocument);
  let timer = null;
  try {
    const result = (await trigger()) || {};
    if (result.errorText) {
      throw new Error(`Navigation failed: ${result.errorText}`);
    }
    if (result.loaderId) {
      committed = { loaderId: result.loaderId, done: false };
    } else if (Object.prototype.hasOwnProperty.call(result, 'frameId')) {
      // Page.navigate without a loaderId is a same-document navigation.
      committed = { loaderId: null, done: true };
    }

    const finished = () => committed && (committed.done || reached.has(committed.loaderId));
    if (!finished()) {
      await new Promise((resolve, reject) => {
        timer = setTimeout(() => {
          reject(new Error(`Timed out after ${timeoutMs} ms waiting for ${waitUntil}`));
        }, timeoutMs);
        wake = () => { if (finished()) resolve(); };
      });
    }
    return result;
  } finally {
    clearTimeout(timer);
    wake = () => {};
    cdp.off('Page.lifecycleEvent', onLifecycle);
    cdp.off('Page.frameNavigated', onFrameNavigated);
    cdp.off('Page.navigatedWithinDocument', onSameDocument);
  }
}

async function pageInfo(cdp) {
  const info = await cdp.send('Runtime.evaluate', {
    expression: `({ title: document.title, url: window.location.href, readyState: document.readyState })`,
    returnByValue: true
  });
  return (info.result && info.result.value) || {};
}

/**
 * Navigate to URL
 */
async function navigate(args, context) {
  const { sessionId, url, waitUntil, referrer, headers, timeout } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Extra headers stay in effect for later requests of this tab.
  if (headers) {
    await cdp.send('Network.setExtraHTTPHeaders', { headers });
  }

  const navigateParams = { url };
  if (referrer) navigateParams.referrer = referrer;
  await runNavigation(cdp, () => cdp.send('Page.navigate', navigateParams), { waitUntil, timeout });

  const info = await pageInfo(cdp);
  return {
    success: true,
    url: info.url || url,
    title: info.title,
    readyState: info.readyState
  };
}

/** Move `delta` entries through the tab's session history. */
async function historyStep(args, delta) {
  const { sessionId, waitUntil, timeout } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const { currentIndex, entries } = await cdp.send('Page.getNavigationHistory');
  const target = entries[currentIndex + delta];
  if (!target) {
    return {
      success: false,
      error: delta < 0 ? 'No previous history entry' : 'No next history entry'
    };
  }
  await runNavigation(cdp, () => cdp.send('Page.navigateToHistoryEntry', { entryId: target.id }), { waitUntil, timeout });
  const info = await pageInfo(cdp);
  return { success: true, url: info.url || target.url, title: info.title };
}

/**
 * Go back
 */
async function goBack(args, context) {
  return historyStep(args, -1);
}

/**
 * Go forward
 */
async function goForward(args, context) {
  return historyStep(args, 1);
}

/**
 * Reload page
 */
async function reload(args, context) {
  const { sessionId, ignoreCache, waitUntil, timeout } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  await runNavigation(cdp, () => cdp.send('Page.reload', { ignoreCache: ignoreCache || false }), { waitUntil, timeout });
  const info = await pageInfo(cdp);
  return { success: true, url: info.url, title: info.title };
}

/**
 * Get current URL and title
 */
async function getCurrentUrl(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const result = await cdp.send('Runtime.evaluate', {
    expression: `({ url: window.location.href, title: document.title, origin: window.location.origin })`,
    returnByValue: true
  });

  return {
    success: true,
    ...(result.result && result.result.value)
  };
}

module.exports = {
  navigate,
  goBack,
  goForward,
  reload,
  getCurrentUrl,
  runNavigation
};
