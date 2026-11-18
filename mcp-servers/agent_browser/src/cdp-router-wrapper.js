/**
 * cdp-router-wrapper.js - Wrapper to connect CDP router with session manager
 * and handle browser lifecycle
 */

const { chromium } = require('playwright');
const { SessionManager } = require('./session-manager');
const { CDPRouter } = require('./cdp-router');
const { buildLaunchArgs, buildCDPEmulationConfig, applyCDPEmulation } = require('./launch-config');

let sessionManager = null;
let cdpRouter = null;
let activeBrowsers = new Map(); // sessionId -> { browser, context }

function getSessionManager() {
  if (!sessionManager) {
    sessionManager = new SessionManager();
  }
  return sessionManager;
}

function getCDPRouter() {
  if (!cdpRouter) {
    cdpRouter = new CDPRouter();
  }
  return cdpRouter;
}

/**
 * Initialize browser for session
 */
async function initializeBrowser(sessionId, config = {}) {
  const mgr = getSessionManager();
  const session = await mgr.getSession(sessionId);

  const launchConfig = {
    headless: config.headless !== false,
    args: buildLaunchArgs({
      viewport: session.viewport,
      locale: session.locale,
      headless: config.headless !== false,
      proxy: session.proxy
    }),
    userDataDir: session.profilePath
  };

  // Launch persistent context
  const browser = await chromium.launchPersistentContext(session.profilePath, {
    executablePath: config.executablePath,
    headless: launchConfig.headless,
    args: launchConfig.args,
    viewport: null, // CLI args only
    ignoreDefaultArgs: ['--enable-automation', '--disable-extensions'],
    userAgent: config.userAgent,
    permissions: ['geolocation', 'notifications', 'camera', 'microphone'],
    timezoneId: session.timezone,
    locale: session.locale,
    geolocation: config.geolocation
  });

  // Get default page
  const pages = browser.pages();
  let page = pages[0];
  if (!page) {
    page = await browser.newPage();
  }

  // Create CDP session for page
  const cdp = await browser.newCDPSession(page);

  // Register with CDP router
  const router = getCDPRouter();
  router.registerSession(sessionId, { browser, context: browser, defaultPage: page });

  // Apply CDP emulation
  const emulationConfig = buildCDPEmulationConfig({
    viewport: session.viewport,
    locale: session.locale,
    timezone: session.timezone,
    userAgent: config.userAgent
  });
  await applyCDPEmulation(cdp, emulationConfig);

  // Store browser reference
  activeBrowsers.set(sessionId, { browser, context: browser });

  // Mark session active
  mgr.markSessionActive(sessionId);

  console.log(`[BrowserLauncher] Session ${sessionId} browser initialized`);
  return { browser, context: browser, page, cdp };
}

/**
 * Get browser for session
 */
async function getBrowser(sessionId) {
  let browserData = activeBrowsers.get(sessionId);

  if (!browserData) {
    // Try to reinitialize
    browserData = await initializeBrowser(sessionId);
  }

  return browserData;
}

/**
 * Close browser for session
 */
async function closeBrowser(sessionId) {
  const browserData = activeBrowsers.get(sessionId);
  if (browserData) {
    try {
      await browserData.context.close();
    } catch (e) {}
    try {
      await browserData.browser.close();
    } catch (e) {}
    activeBrowsers.delete(sessionId);
  }

  const mgr = getSessionManager();
  mgr.markSessionClosed(sessionId);

  console.log(`[BrowserLauncher] Session ${sessionId} browser closed`);
}

/**
 * Get or create page CDP session
 */
async function getPageCDP(sessionId, pageId = 'default') {
  const router = getCDPRouter();
  return router.getPageCDP(sessionId, pageId);
}

/**
 * Create new page
 */
async function createPage(sessionId, url = 'about:blank') {
  const router = getCDPRouter();
  return router.createPage(sessionId, url);
}

/**
 * Switch tab
 */
async function switchTab(sessionId, pageId) {
  const router = getCDPRouter();
  return router.bringToFront(sessionId, pageId);
}

/**
 * Close page
 */
async function closePage(sessionId, pageId) {
  const router = getCDPRouter();
  return router.closePage(sessionId, pageId);
}

/**
 * List pages
 */
function listPages(sessionId) {
  const router = getCDPRouter();
  return router.getPages(sessionId);
}

/**
 * Send CDP command
 */
async function sendCDP(sessionId, domain, method, params, target) {
  const router = getCDPRouter();
  return router.sendCDP(sessionId, domain, method, params, target);
}

/**
 * Evaluate JavaScript
 */
async function evaluate(sessionId, expression, options) {
  const router = getCDPRouter();
  return router.evaluate(sessionId, expression, options);
}

/**
 * Subscribe to CDP events
 */
async function subscribe(sessionId, domain, event, filter) {
  const router = getCDPRouter();
  return router.subscribe(sessionId, domain, event, filter);
}

/**
 * Get session manager
 */
function getSessionManagerInstance() {
  return getSessionManager();
}

/**
 * Get CDP router
 */
function getCDPRouterInstance() {
  return getCDPRouter();
}

module.exports = {
  initializeBrowser,
  getBrowser,
  closeBrowser,
  getPageCDP,
  createPage,
  switchTab,
  closePage,
  listPages,
  sendCDP,
  evaluate,
  subscribe,
  getSessionManagerInstance,
  getCDPRouterInstance,
  activeBrowsers
};