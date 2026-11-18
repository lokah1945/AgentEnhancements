/**
 * navigation.js - Navigation MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');

/**
 * Navigate to URL
 */
async function navigate(args, context) {
  const { sessionId, url, waitUntil, referrer, headers } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Set referrer if provided
  if (referrer) {
    await cdp.send('Network.setExtraHTTPHeaders', {
      headers: { 'Referer': referrer }
    });
  }

  // Set custom headers if provided
  if (headers) {
    await cdp.send('Network.setExtraHTTPHeaders', { headers });
  }

  // Navigate
  await cdp.send('Page.navigate', { url });

  // Wait for load event
  const waitEvent = waitUntil === 'networkIdle' ? 'networkIdle' :
                    waitUntil === 'load' ? 'loadEventFired' : 'domContentLoaded';

  if (waitEvent !== 'domContentLoaded') {
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Navigation timeout')), 30000);
      cdp.once(`Page.${waitEvent}`, () => {
        clearTimeout(timeout);
        resolve();
      });
    });
  } else {
    await cdp.send('Page.domContentLoaded');
  }

  // Get page info
  const pageInfo = await cdp.send('Runtime.evaluate', {
    expression: `({ title: document.title, url: window.location.href, readyState: document.readyState })`,
    returnByValue: true
  });

  return {
    success: true,
    url: pageInfo.result?.value?.url || url,
    title: pageInfo.result?.value?.title,
    readyState: pageInfo.result?.value?.readyState
  };
}

/**
 * Go back
 */
async function goBack(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  await cdp.send('Page.goBack');
  await cdp.send('Page.domContentLoaded');

  return { success: true };
}

/**
 * Go forward
 */
async function goForward(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  await cdp.send('Page.goForward');
  await cdp.send('Page.domContentLoaded');

  return { success: true };
}

/**
 * Reload page
 */
async function reload(args, context) {
  const { sessionId, ignoreCache } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  await cdp.send('Page.reload', { ignoreCache: ignoreCache || false });
  await cdp.send('Page.domContentLoaded');

  return { success: true };
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
    ...result.result?.value
  };
}

module.exports = {
  navigate,
  goBack,
  goForward,
  reload,
  getCurrentUrl
};