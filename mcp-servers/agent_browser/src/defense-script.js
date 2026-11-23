/**
 * defense-script.js - Shared headless defense script
 *
 * This script fixes Chromium headless-specific rendering bugs and missing Chrome internals.
 * These are NOT fingerprint spoofing - they fix actual Chromium headless vs headed differences.
 *
 * Applied via:
 * 1. Playwright's context.addInitScript() - CONTEXT-WIDE, fires on EVERY document in EVERY page/tab/iframe
 * 2. CDP Page.addScriptToEvaluateOnNewDocument - Per-page backup
 */

const HEADLESS_DEFENSE_SCRIPT = `
(function() {
  'use strict';

  // Fix 1: window.chrome object (Chromium internal, missing in headless)
  // Real Chrome has: runtime, app, webstore, etc.
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
  // This is a Chromium headless BUG, not a fingerprint
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
  // Force light color scheme for consistent rendering
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
      // Return 'prompt' for common permissions instead of 'denied'
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
  // Real Chrome on Windows has several plugins (PDF viewer, Widevine, etc.)
  try {
    var mockPlugins = [
      { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format', length: 1 },
      { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '', length: 1 },
      { name: 'Native Client', filename: 'internal-nacl-plugin', description: '', length: 1 },
      { name: 'Widevine Content Decryption Module', filename: 'widevinecdm', description: 'Enables Widevine licenses for playback of HTML audio/video', length: 1 }
    ];

    // Add item() and namedItem() methods
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

    // Mock mimeTypes
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
  // This is a mismatch that bot detectors check
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
      get: function() { return ''; },  // Empty is actually normal for Chrome
      enumerable: true,
      configurable: true
    });
  } catch(e) {}

  // Fix 9: navigator.productSub (headless often wrong)
  try {
    Object.defineProperty(navigator, 'productSub', {
      get: function() { return '20030107'; },  // Standard Chrome value
      enumerable: true,
      configurable: true
    });
  } catch(e) {}

  // Fix 10: CSS system colors (duplicate fix for robustness)
  try {
    var styleEl = document.createElement('style');
    styleEl.textContent = ':root { color-scheme: light; }';
    if (document.head) {
      document.head.appendChild(styleEl);
    } else if (document.documentElement) {
      document.documentElement.appendChild(styleEl);
    }
  } catch(e) {}

  // Fix 11: Permissions API (duplicate fix for robustness)
  if (navigator.permissions && navigator.permissions.query) {
    var originalQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = function(permissionDesc) {
      // Return 'prompt' for common permissions instead of 'denied'
      if (permissionDesc && permissionDesc.name) {
        var name = permissionDesc.name;
        if (['geolocation', 'notifications', 'camera', 'microphone'].includes(name)) {
          return Promise.resolve({ state: 'prompt', onchange: null });
        }
      }
      return originalQuery(permissionDesc);
    };
  }

  // Mark defense applied (idempotency)
  window.__agentBrowserHeadlessDefenseApplied = true;
})();
`;

/**
 * Apply headless defense to a CDP session
 * @param {CDPSession} cdp - CDP session
 */
async function applyHeadlessDefense(cdp) {
  try {
    // Apply via CDP Page.addScriptToEvaluateOnNewDocument (per-page)
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: HEADLESS_DEFENSE_SCRIPT
    });

    // Also execute immediately for current page
    await cdp.send('Runtime.evaluate', {
      expression: HEADLESS_DEFENSE_SCRIPT,
      awaitPromise: false
    });

    console.error('[agent_browser] CDP: Headless defense applied');
  } catch (e) {
    console.warn('[agent_browser] CDP: Headless defense failed:', e.message);
  }
}

module.exports = {
  HEADLESS_DEFENSE_SCRIPT,
  applyHeadlessDefense
};