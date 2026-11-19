/**
 * cdp-router-wrapper.js - Wrapper to connect CDP router with session manager
 * and handle browser lifecycle
 */

const { chromium } = require('playwright');
const { SessionManager } = require('./session-manager');
const { CDPRouter } = require('./cdp-router');
const { buildLaunchArgs, buildCDPEmulationConfig, applyCDPEmulation } = require('./launch-config');
const { HEADLESS_DEFENSE_SCRIPT, applyHeadlessDefense } = require('./defense-script');

let sessionManager = null;
let cdpRouter = null;
let activeBrowsers = new Map(); // sessionId -> { browser, context }
// Track pending initializations to prevent race conditions
const initLocks = new Map(); // sessionId -> Promise

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
  // Prevent race condition: if initialization already in progress, wait for it
  if (initLocks.has(sessionId)) {
    console.log(`[BrowserLauncher] Session ${sessionId} initialization already in progress, waiting...`);
    return initLocks.get(sessionId);
  }

  const initPromise = (async () => {
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

  // CRITICAL: Use Playwright's context.addInitScript() for CONTEXT-WIDE injection
  // This fires on EVERY document in EVERY page/tab/popup/iframe in this context
  // This is the PRIMARY guarantee that all pages/frames get injected with defense
  // No browser-level CDP session needed - addInitScript covers all frames!
  const defenseScript = `
    (function() {
      'use strict';

      // Fix 1: window.chrome object (Chromium internal, missing in headless)
      if (!window.chrome) {
        try {
          window.chrome = {
            runtime: {
              id: '',
              onConnect: null,
              onConnectExternal: null,
              onInstalled: null,
              onMessage: null,
              onMessageExternal: null,
              onRestartRequired: null,
              onStartup: null,
              onSuspend: null,
              onSuspendCanceled: null,
              onUpdateAvailable: null,
              connect: function() {},
              connectNative: function() {},
              getBackgroundPage: function() {},
              getManifest: function() { return {}; },
              getPackageDirectoryEntry: function() {},
              getPlatformInfo: function() {},
              reload: function() {},
              requestUpdateCheck: function() {},
              sendMessage: function() {},
              sendNativeMessage: function() {},
              setUninstallURL: function() {}
            },
            app: { isInstalled: false },
            webstore: { onInstallStageChanged: null, onDownloadProgress: null },
            csi: function() {},
            loadTimes: function() {}
          };
        } catch(e) {}
      }

      // Fix 2: Window bar visibility (headless returns false, headed returns true)
      var barNames = ['toolbar', 'menubar', 'personalbar', 'statusbar', 'scrollbars', 'locationbar'];
      for (var i = 0; i < barNames.length; i++) {
        var barName = barNames[i];
        try {
          var bar = window[barName];
          if (bar && typeof bar === 'object') {
            Object.defineProperty(bar, 'visible', {
              get: function() { return true; },
              enumerable: true,
              configurable: true
            });
          }
        } catch(e) {}
      }

      // Fix 3: Notification.permission (headless often 'denied', headed varies)
      if (window.Notification && typeof window.Notification.permission === 'string') {
        try {
          Object.defineProperty(window.Notification, 'permission', {
            get: function() { return 'default'; },
            enumerable: true,
            configurable: true
          });
        } catch(e) {}
      }

      // Fix 4: CSS system colors (headless renders dark, headed renders light)
      try {
        var styleEl = document.createElement('style');
        styleEl.textContent = ':root { color-scheme: light; }';
        if (document.head) {
          document.head.appendChild(styleEl);
        } else if (document.documentElement) {
          document.documentElement.appendChild(styleEl);
        }
      } catch(e) {}

      // Fix 5: Permissions API (headless may behave differently)
      if (navigator.permissions && navigator.permissions.query) {
        var originalQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(permissionDesc) {
          if (permissionDesc && permissionDesc.name) {
            var name = permissionDesc.name;
            if (['geolocation', 'notifications', 'camera', 'microphone'].includes(name)) {
              return Promise.resolve({ state: 'prompt', onchange: null });
            }
          }
          return originalQuery(permissionDesc);
        };
      }

      // Fix 6: navigator.plugins / mimeTypes (headless may be empty)
      try {
        var mockPlugins = [
          { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1 },
          { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1 },
          { name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 1 },
          { name: 'Widevine Content Decryption Module', filename: 'widevinecdm', description: 'Enables Widevine licenses for playback of HTML audio/video', length: 1 }
        ];
        mockPlugins.item = function(index) { return this[index] || null; };
        mockPlugins.namedItem = function(name) {
          for (var i = 0; i < this.length; i++) {
            if (this[i].name === name) return this[i];
          }
          return null;
        };
        mockPlugins.refresh = function() {};

        Object.defineProperty(navigator, 'plugins', {
          get: function() { return mockPlugins; },
          enumerable: true,
          configurable: true
        });

        var mockMimeTypes = [
          { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: mockPlugins[0] },
          { type: 'application/x-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: mockPlugins[0] },
          { type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format', enabledPlugin: mockPlugins[1] },
          { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable', enabledPlugin: mockPlugins[2] },
          { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable', enabledPlugin: mockPlugins[2] }
        ];
        mockMimeTypes.item = function(index) { return this[index] || null; };
        mockMimeTypes.namedItem = function(name) {
          for (var i = 0; i < this.length; i++) {
            if (this[i].type === name) return this[i];
          }
          return null;
        };

        Object.defineProperty(navigator, 'mimeTypes', {
          get: function() { return mockMimeTypes; },
          enumerable: true,
          configurable: true
        });
      } catch(e) {}

      // Fix 7: navigator.platform (headless shows Linux, but UA says Windows)
      try {
        Object.defineProperty(navigator, 'platform', {
          get: function() { return 'Win32'; },
          enumerable: true,
          configurable: true
        });
      } catch(e) {}

      // Fix 8: navigator.vendorSub (headless often empty)
      try {
        Object.defineProperty(navigator, 'vendorSub', {
          get: function() { return ''; },
          enumerable: true,
          configurable: true
        });
      } catch(e) {}

      // Fix 9: navigator.productSub (headless often wrong)
      try {
        Object.defineProperty(navigator, 'productSub', {
          get: function() { return '20030107'; },
          enumerable: true,
          configurable: true
        });
      } catch(e) {}

      // Fix 10: CSS system colors
      try {
        var styleEl = document.createElement('style');
        styleEl.textContent = ':root { color-scheme: light; }';
        if (document.head) {
          document.head.appendChild(styleEl);
        } else if (document.documentElement) {
          document.documentElement.appendChild(styleEl);
        }
      } catch(e) {}

      // Fix 11: Permissions API
      if (navigator.permissions && navigator.permissions.query) {
        var originalQuery = navigator.permissions.query.bind(navigator.permissions);
        navigator.permissions.query = function(permissionDesc) {
          if (permissionDesc && permissionDesc.name) {
            var name = permissionDesc.name;
            if (['geolocation', 'notifications', 'camera', 'microphone'].includes(name)) {
              return Promise.resolve({ state: 'prompt', onchange: null });
            }
          }
          return originalQuery(permissionDesc);
        };
      }

      window.__agentBrowserHeadlessDefenseApplied = true;
    })();
  `;

  // PRIMARY: context.addInitScript() - CONTEXT-WIDE, fires on EVERY document
  await browser.addInitScript(defenseScript);
  console.log('[agent_browser] Context-wide headless defense registered (addInitScript)');

  // REINFORCEMENT: CDP Page.addScriptToEvaluateOnNewDocument - per-page backup
  await cdp.send('Page.addScriptToEvaluateOnNewDocument', { source: defenseScript });
  console.log('[agent_browser] CDP per-page defense registered');

  // Build emulation config
  const emulationConfig = buildCDPEmulationConfig({
    viewport: session.viewport,
    locale: session.locale,
    timezone: session.timezone,
    userAgent: config.userAgent
  });

  // Apply CDP emulation to initial page
  await applyCDPEmulation(cdp, emulationConfig);

  // Register with CDP router (pass emulationConfig for new pages)
  const router = getCDPRouter();
  router.registerSession(sessionId, { browser, context: browser, defaultPage: page, emulationConfig });

  // Store browser reference
  activeBrowsers.set(sessionId, { browser, context: browser });

  // Mark session active
  mgr.markSessionActive(sessionId);

  console.log(`[BrowserLauncher] Session ${sessionId} browser initialized`);
  return { browser, context: browser, page, cdp };
  })();

  // Store the promise in the lock map
  initLocks.set(sessionId, initPromise);

  try {
    const result = await initPromise;
    return result;
  } finally {
    // Release the lock
    initLocks.delete(sessionId);
  }
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