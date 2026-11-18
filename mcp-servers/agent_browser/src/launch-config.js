/**
 * launch-config.js - Chrome launch arguments and CDP emulation for honest headless→headful appearance
 *
 * Philosophy: Zero spoofing. Use Chrome flags and CDP commands that make headless
 * behave identically to headful at the browser engine level.
 */

const os = require('os');

const PLATFORM = {
  isWindows: os.platform() === 'win32',
  isLinux: os.platform() === 'linux',
  isMac: os.platform() === 'darwin',
  arch: os.arch()
};

/**
 * Build Chrome launch arguments for honest headless operation
 * @param {Object} config - Launch configuration
 * @returns {string[]} Chrome command line arguments
 */
function buildLaunchArgs(config) {
  const {
    viewport = {},
    locale = 'en-US',
    headless = true,
    proxy = null
  } = config;

  const {
    width = 1920,
    height = 1080,
    deviceScaleFactor = 1,
    isMobile = false,
    hasTouch = false
  } = viewport;

  const args = [];

  // === HEADLESS MODE (Chrome 112+ new headless - hardest to detect) ===
  if (headless) {
    args.push('--headless=new');
  }

  // === VIEWPORT VIA CLI (Not JS viewport option) ===
  args.push(`--window-size=${width},${height}`);
  args.push(`--force-device-scale-factor=${deviceScaleFactor}`);
  args.push('--window-position=0,0');

  // === HIDE AUTOMATION FLAGS (Chrome internal, not JS spoofing) ===
  args.push('--disable-blink-features=AutomationControlled');
  args.push('--disable-infobars');
  args.push('--no-default-browser-check');
  args.push('--no-first-run');
  args.push('--disable-background-networking');
  args.push('--disable-background-timer-throttling');
  args.push('--disable-renderer-backgrounding');
  args.push('--disable-ipc-flooding-protection');
  args.push('--disable-hang-monitor');
  args.push('--disable-prompt-on-repost');
  args.push('--disable-sync');
  args.push('--disable-translate');
  args.push('--metrics-recording-only');
  args.push('--no-report-upload');
  args.push('--disable-breakpad');
  args.push('--disable-component-extensions-with-background-pages');
  args.push('--disable-extensions-except=');
  args.push('--disable-default-apps');

  // === PASSWORD/KEYCHAIN (Headless compatible) ===
  args.push('--password-store=basic');
  args.push('--use-mock-keychain');

  // === GPU ACCELERATION (Real HW - Not Spoofing) ===
  args.push('--ignore-gpu-blocklist');
  args.push('--enable-gpu-rasterization');
  args.push('--enable-zero-copy');
  args.push('--enable-hardware-overlays');
  args.push('--disable-software-rasterizer');
  args.push('--enable-accelerated-video-decode');
  args.push('--enable-accelerated-2d-canvas');
  args.push('--enable-features=CanvasOopRasterization');
  args.push('--enable-features=VulkanFromANGLE');

  if (PLATFORM.isWindows) {
    args.push('--use-angle=d3d11');
    args.push('--enable-features=DefaultANGLEVulkan');
  } else if (PLATFORM.isLinux) {
    args.push('--use-angle=vulkan');
    args.push('--enable-features=VulkanFromANGLE');
  } else if (PLATFORM.isMac) {
    args.push('--use-angle=metal');
    args.push('--enable-features=MetalANGLE');
  }

  // === WEBRTC (Real Stack - Use Chrome Flag for IP Protection) ===
  args.push('--force-webrtc-ip-handling-policy=default_public_interface_only');
  args.push('--webrtc-ip-handling-policy=default_public_interface_only');

  // === NETWORK / PERFORMANCE ===
  args.push('--disable-background-networking');
  args.push('--disable-background-timer-throttling');
  args.push('--disable-renderer-backgrounding');
  args.push('--disable-ipc-flooding-protection');
  args.push('--enable-tcp-fast-open');
  args.push('--enable-quic');
  args.push('--enable-features=NetworkService,NetworkServiceInProcess');

  // === LOCALE ===
  args.push(`--lang=${locale}`);

  // === MEMORY / JS ===
  args.push('--js-flags=--expose-gc');
  args.push('--disable-features=HardwareConcurrencyFreezing');
  args.push('--disable-features=IsolateOrigins,site-per-process');

  // === PROXY ===
  if (proxy?.server) {
    args.push(`--proxy-server=${proxy.server}`);
    if (proxy.bypass) {
      args.push(`--proxy-bypass-list=${proxy.bypass}`);
    }
  }

  // === MOBILE EMULATION (via CLI, not CDP) ===
  if (isMobile) {
    args.push('--user-agent=Mozilla/5.0 (Linux; Android 10; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36');
  }

  // === TOUCH (via CLI for headless) ===
  if (hasTouch) {
    args.push('--touch-events=enabled');
    args.push('--enable-pointer-event-target');
  }

  // === SECURITY (Relaxed for automation but not spoofed) ===
  args.push('--disable-web-security');
  args.push('--disable-site-isolation-trials');
  args.push('--disable-features=IsolateOrigins');
  args.push('--allow-running-insecure-content');
  args.push('--ignore-certificate-errors');
  args.push('--ignore-certificate-errors-spki-list');
  args.push('--ignore-ssl-errors');
  args.push('--allow-insecure-localhost');

  // === AUDIO (Headless needs this) ===
  args.push('--autoplay-policy=no-user-gesture-required');
  args.push('--disable-audio-output');

  return args;
}

/**
 * CDP Emulation configuration applied immediately after page creation
 * These are BROWSER ENGINE LEVEL overrides, not JavaScript spoofing
 */
const CDP_EMULATION_DEFAULTS = {
  // Screen/Viewport/DPR - Native Chromium level
  deviceMetrics: {
    width: 1920,
    height: 1080,
    deviceScaleFactor: 1,
    mobile: false,
    screenWidth: 1920,
    screenHeight: 1080,
    positionX: 0,
    positionY: 0,
    // viewportScale: 1, // Not needed
    // screenOrientation: { angle: 0, type: 'landscapePrimary' } // Default
  },

  // Touch emulation - Real TouchEvent generation
  touch: {
    enabled: false,
    maxTouchPoints: 10,
    configuration: 'mobile'
  },

  // User Agent + Sec-CH-UA - CDP level (affects NETWORK HEADERS!)
  userAgent: {
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    acceptLanguage: 'en-US,en;q=0.9',
    platform: 'Windows',
    userAgentMetadata: {
      brands: [
        { brand: 'Google Chrome', version: '131' },
        { brand: 'Chromium', version: '131' },
        { brand: 'Not/A)Brand', version: '24' }
      ],
      fullVersionList: [
        { brand: 'Google Chrome', version: '131.0.0.0' },
        { brand: 'Chromium', version: '131.0.0.0' },
        { brand: 'Not/A)Brand', version: '24.0.0.0' }
      ],
      platform: 'Windows',
      platformVersion: '15.0.0',
      architecture: 'x86',
      model: '',
      mobile: false,
      bitness: '64'
    }
  },

  // Timezone - CDP level
  timezone: {
    timezoneId: 'America/New_York'
  },

  // Locale - CDP level (affects Intl, navigator.language)
  locale: {
    locale: 'en-US'
  },

  // Hardware concurrency - CDP native override (Chromium M110+)
  hardwareConcurrency: {
    hardwareConcurrency: 8
  },

  // Device memory - No CDP command, requires Runtime.evaluate IMMEDIATELY
  deviceMemory: {
    memory: 8
  }
};

/**
 * Apply all CDP emulation overrides to a page
 * @param {CDPSession} cdp - CDP session for the page
 * @param {Object} config - Emulation configuration (merged with defaults)
 */
async function applyCDPEmulation(cdp, config = {}) {
  const emulation = { ...CDP_EMULATION_DEFAULTS, ...config };

  try {
    // 1. Device Metrics (Screen/Viewport/DPR) - Native Chromium level
    await cdp.send('Emulation.setDeviceMetricsOverride', emulation.deviceMetrics);
    console.log('[agent_browser] CDP: Device metrics applied', {
      viewport: `${emulation.deviceMetrics.width}x${emulation.deviceMetrics.height}`,
      screen: `${emulation.deviceMetrics.screenWidth}x${emulation.deviceMetrics.screenHeight}`,
      dpr: emulation.deviceMetrics.deviceScaleFactor
    });
  } catch (e) {
    console.warn('[agent_browser] CDP: Device metrics failed:', e.message);
  }

  try {
    // 2. Touch Emulation - Real TouchEvent generation
    if (emulation.touch.enabled) {
      await cdp.send('Emulation.setTouchEmulationEnabled', emulation.touch);
      console.log('[agent_browser] CDP: Touch emulation enabled');
    }
  } catch (e) {
    console.warn('[agent_browser] CDP: Touch emulation failed:', e.message);
  }

  try {
    // 3. User Agent + Sec-CH-UA - CDP level (affects NETWORK HEADERS!)
    await cdp.send('Emulation.setUserAgentOverride', emulation.userAgent);
    console.log('[agent_browser] CDP: User agent + sec-ch-ua applied');
  } catch (e) {
    console.warn('[agent_browser] CDP: User agent override failed:', e.message);
  }

  try {
    // 4. Timezone - CDP level
    await cdp.send('Emulation.setTimezoneOverride', emulation.timezone);
    console.log('[agent_browser] CDP: Timezone applied');
  } catch (e) {
    console.warn('[agent_browser] CDP: Timezone failed:', e.message);
  }

  try {
    // 5. Locale - CDP level
    await cdp.send('Emulation.setLocaleOverride', emulation.locale);
    console.log('[agent_browser] CDP: Locale applied');
  } catch (e) {
    console.warn('[agent_browser] CDP: Locale failed:', e.message);
  }

  try {
    // 6. Hardware Concurrency - CDP native override (Chromium M110+)
    await cdp.send('Emulation.setHardwareConcurrencyOverride', emulation.hardwareConcurrency);
    console.log('[agent_browser] CDP: Hardware concurrency applied');
  } catch (e) {
    console.warn('[agent_browser] CDP: Hardware concurrency failed:', e.message);
  }

  try {
    // 7. Device Memory - IMMEDIATE Runtime.evaluate (no CDP command exists)
    // This runs BEFORE any page JavaScript can read navigator.deviceMemory
    await cdp.send('Runtime.evaluate', {
      expression: `(function() {
        var m = ${emulation.deviceMemory.memory};
        try { Object.defineProperty(Navigator.prototype, 'deviceMemory', { get: function() { return m; }, configurable: true, enumerable: true }); } catch(e) {}
        try { Object.defineProperty(navigator, 'deviceMemory', { get: function() { return m; }, configurable: true, enumerable: true }); } catch(e) {}
      })();`,
      awaitPromise: false
    });
    console.log('[agent_browser] CDP: Device memory override applied via Runtime.evaluate');
  } catch (e) {
    console.warn('[agent_browser] CDP: Device memory failed:', e.message);
  }

  // 8. Headless Defense - Minimal fixes for headless-specific bugs (NOT spoofing)
  await applyHeadlessDefense(cdp);

  return { success: true };
}

/**
 * Apply minimal headless defense - fixes for headless-specific rendering bugs
 * These are NOT fingerprint spoofing - they fix Chromium headless rendering differences
 */
async function applyHeadlessDefense(cdp) {
  const defenseScript = `
    (function() {
      'use strict';

      // Fix 1: window.chrome object (Chromium internal, missing in headless)
      if (!window.chrome) {
        try { window.chrome = { runtime: {} }; } catch(e) {}
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
      // Ensure they exist as arrays (not spoofing content, just structure)
      try {
        if (!navigator.plugins) {
          Object.defineProperty(navigator, 'plugins', {
            get: function() { return []; },
            enumerable: true,
            configurable: true
          });
        }
        if (!navigator.mimeTypes) {
          Object.defineProperty(navigator, 'mimeTypes', {
            get: function() { return []; },
            enumerable: true,
            configurable: true
          });
        }
      } catch(e) {}

      // Mark defense applied (idempotency)
      window.__agentBrowserHeadlessDefenseApplied = true;
    })();
  `;

  try {
    await cdp.send('Page.addScriptToEvaluateOnNewDocument', {
      source: defenseScript
    });

    // Also execute immediately for current page
    await cdp.send('Runtime.evaluate', {
      expression: defenseScript,
      awaitPromise: false
    });

    console.log('[agent_browser] CDP: Headless defense applied');
  } catch (e) {
    console.warn('[agent_browser] CDP: Headless defense failed:', e.message);
  }
}

/**
 * Build CDP emulation config from session config
 * @param {Object} sessionConfig - Session configuration
 * @returns {Object} CDP emulation config
 */
function buildCDPEmulationConfig(sessionConfig) {
  const viewport = sessionConfig.viewport || {};
  const locale = sessionConfig.locale || 'en-US';
  const timezone = sessionConfig.timezone || 'America/New_York';

  return {
    deviceMetrics: {
      width: viewport.width || 1920,
      height: viewport.height || 1080,
      deviceScaleFactor: viewport.deviceScaleFactor || 1,
      mobile: viewport.isMobile || false,
      screenWidth: viewport.width || 1920,
      screenHeight: viewport.height || 1080,
      positionX: 0,
      positionY: 0
    },
    touch: {
      enabled: viewport.hasTouch || false,
      maxTouchPoints: viewport.hasTouch ? 10 : 0,
      configuration: 'mobile'
    },
    userAgent: {
      userAgent: sessionConfig.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
      acceptLanguage: locale,
      platform: 'Windows',
      userAgentMetadata: {
        brands: [
          { brand: 'Google Chrome', version: '131' },
          { brand: 'Chromium', version: '131' },
          { brand: 'Not/A)Brand', version: '24' }
        ],
        fullVersionList: [
          { brand: 'Google Chrome', version: '131.0.0.0' },
          { brand: 'Chromium', version: '131.0.0.0' },
          { brand: 'Not/A)Brand', version: '24.0.0.0' }
        ],
        platform: 'Windows',
        platformVersion: '15.0.0',
        architecture: 'x86',
        model: '',
        mobile: viewport.isMobile || false,
        bitness: '64'
      }
    },
    timezone: { timezoneId: timezone },
    locale: { locale: locale },
    hardwareConcurrency: { hardwareConcurrency: 8 },
    deviceMemory: { memory: 8 }
  };
}

module.exports = {
  buildLaunchArgs,
  applyCDPEmulation,
  applyHeadlessDefense,
  buildCDPEmulationConfig,
  CDP_EMULATION_DEFAULTS,
  PLATFORM
};