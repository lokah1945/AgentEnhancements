/**
 * tabs.js - Tab management MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');

/**
 * Create new tab
 */
async function tabNew(args, context) {
  const { sessionId, url, background } = args;

  const router = getCDPRouter();
  const result = await router.createPage(sessionId, url || 'about:blank');

  if (!background) {
    await router.bringToFront(sessionId, result.pageId);
  }

  return {
    success: true,
    pageId: result.pageId,
    url: url || 'about:blank'
  };
}

/**
 * Switch tab
 */
async function tabSwitch(args, context) {
  const { sessionId, tabIndex, tabId } = args;

  const router = getCDPRouter();

  let pageId = tabId;
  if (tabIndex !== undefined) {
    const pages = await router.getPages(sessionId);
    if (tabIndex >= 0 && tabIndex < pages.length) {
      pageId = pages[tabIndex].pageId;
    } else {
      throw new Error(`Tab index out of range: ${tabIndex}`);
    }
  }

  if (!pageId) {
    throw new Error('Either tabIndex or tabId must be provided');
  }

  await router.bringToFront(sessionId, pageId);

  return { success: true, pageId };
}

/**
 * Close tab
 */
async function tabClose(args, context) {
  const { sessionId, tabIndex, tabId } = args;

  const router = getCDPRouter();

  let pageId = tabId;
  if (tabIndex !== undefined) {
    const pages = await router.getPages(sessionId);
    if (tabIndex >= 0 && tabIndex < pages.length) {
      pageId = pages[tabIndex].pageId;
    } else {
      throw new Error(`Tab index out of range: ${tabIndex}`);
    }
  }

  if (!pageId) {
    throw new Error('Either tabIndex or tabId must be provided');
  }

  await router.closePage(sessionId, pageId);

  return { success: true };
}

/**
 * List tabs
 */
async function tabList(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const pages = await router.getPages(sessionId);

  return {
    success: true,
    tabs: pages.map((p, i) => ({
      index: i,
      pageId: p.pageId,
      url: p.url,
      title: p.title,
      active: p.active
    })),
    count: pages.length
  };
}

/**
 * Get tab info
 */
async function tabGet(args, context) {
  const { sessionId, tabIndex, tabId } = args;

  const router = getCDPRouter();

  let pageId = tabId;
  if (tabIndex !== undefined) {
    const pages = await router.getPages(sessionId);
    if (tabIndex >= 0 && tabIndex < pages.length) {
      pageId = pages[tabIndex].pageId;
    } else {
      throw new Error(`Tab index out of range: ${tabIndex}`);
    }
  }

  if (!pageId) {
    throw new Error('Either tabIndex or tabId must be provided');
  }

  const cdp = await router.getPageCDP(sessionId, pageId);
  const result = await cdp.send('Runtime.evaluate', {
    expression: `({ url: window.location.href, title: document.title, readyState: document.readyState })`,
    returnByValue: true
  });

  return {
    success: true,
    pageId,
    ...result.result?.value
  };
}

module.exports = {
  tabNew,
  tabSwitch,
  tabClose,
  tabList,
  tabGet
};