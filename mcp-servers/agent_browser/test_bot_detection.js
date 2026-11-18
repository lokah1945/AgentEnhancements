const { chromium } = require('playwright');
const { buildLaunchArgs, applyCDPEmulation, buildCDPEmulationConfig } = require('/root/project/AgentEnhancements/mcp-servers/agent_browser/src/launch-config');

async function testBotDetection() {
  console.log('[Test] Launching browser with honest headless emulation...');

  const launchArgs = buildLaunchArgs({
    viewport: { width: 1920, height: 1080, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
    locale: 'en-US',
    headless: true,
    proxy: null
  });

  console.log('[Test] Launch args:', launchArgs.join(' '));

  const browser = await chromium.launchPersistentContext('/tmp/test-profile-bot', {
    headless: true,
    args: launchArgs,
    viewport: null,
    ignoreDefaultArgs: ['--enable-automation', '--disable-extensions'],
    permissions: ['geolocation'],
    timezoneId: 'America/New_York',
    locale: 'en-US'
  });

  const page = browser.pages()[0] || await browser.newPage();
  const cdp = await browser.newCDPSession(page);

  // Apply CDP emulation
  const emulationConfig = buildCDPEmulationConfig({
    viewport: { width: 1920, height: 1080, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
    locale: 'en-US',
    timezone: 'America/New_York'
  });

  await applyCDPEmulation(cdp, emulationConfig);

  // Test 1: Check navigator.webdriver
  const webdriver = await page.evaluate(() => navigator.webdriver);
  console.log('[Test] navigator.webdriver:', webdriver);

  // Test 2: Check window.chrome
  const chrome = await page.evaluate(() => !!window.chrome);
  console.log('[Test] window.chrome exists:', chrome);

  // Test 3: Check window.toolbar.visible
  const toolbarVisible = await page.evaluate(() => window.toolbar?.visible);
  console.log('[Test] window.toolbar.visible:', toolbarVisible);

  // Test 4: Check screen dimensions
  const screenInfo = await page.evaluate(() => ({
    width: screen.width,
    height: screen.height,
    availWidth: screen.availWidth,
    availHeight: screen.availHeight,
    outerWidth: window.outerWidth,
    outerHeight: window.outerHeight
  }));
  console.log('[Test] Screen info:', JSON.stringify(screenInfo, null, 2));

  // Test 5: Check navigator properties
  const navInfo = await page.evaluate(() => ({
    userAgent: navigator.userAgent,
    hardwareConcurrency: navigator.hardwareConcurrency,
    deviceMemory: navigator.deviceMemory,
    maxTouchPoints: navigator.maxTouchPoints,
    platform: navigator.platform,
    language: navigator.language,
    languages: navigator.languages
  }));
  console.log('[Test] Navigator info:', JSON.stringify(navInfo, null, 2));

  // Test 6: Check sec-ch-ua headers via fetch
  const headers = await page.evaluate(async () => {
    const resp = await fetch('https://httpbin.org/headers');
    return resp.json();
  }).catch(e => ({ error: e.message }));
  console.log('[Test] Request headers:', JSON.stringify(headers, null, 2));

  // Test 7: Canvas fingerprint
  const canvasHash = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 50;
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillText('Bot detection test 🤖', 2, 2);
    return canvas.toDataURL();
  });
  console.log('[Test] Canvas hash (first 100 chars):', canvasHash.substring(0, 100));

  // Test 8: WebGL fingerprint
  const webglInfo = await page.evaluate(() => {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return { error: 'No WebGL' };
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      vendor: gl.getParameter(debugInfo?.UNMASKED_VENDOR_WEBGL || 37445),
      renderer: gl.getParameter(debugInfo?.UNMASKED_RENDERER_WEBGL || 37446),
      version: gl.getParameter(gl.VERSION),
      shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION)
    };
  });
  console.log('[Test] WebGL info:', JSON.stringify(webglInfo, null, 2));

  // Test 9: Audio fingerprint
  const audioHash = await page.evaluate(async () => {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = ctx.createOscillator();
    const analyser = ctx.createAnalyser();
    const gainNode = ctx.createGain();
    oscillator.connect(analyser);
    analyser.connect(gainNode);
    gainNode.connect(ctx.destination);
    oscillator.frequency.value = 10000;
    gainNode.gain.value = 0;
    oscillator.start(0);
    await new Promise(r => setTimeout(r, 100));
    const data = new Float32Array(analyser.frequencyBinCount);
    analyser.getFloatFrequencyData(data);
    oscillator.stop();
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      hash = Math.imul(31, hash) + Math.abs(data[i] * 1000) | 0;
    }
    return hash.toString(16);
  }).catch(e => ({ error: e.message }));
  console.log('[Test] Audio hash:', audioHash);

  // Test 10: Check Notification.permission
  const notifPerm = await page.evaluate(() => Notification.permission);
  console.log('[Test] Notification.permission:', notifPerm);

  // Test 11: Check matchMedia color-scheme
  const colorScheme = await page.evaluate(() => {
    return {
      light: window.matchMedia('(prefers-color-scheme: light)').matches,
      dark: window.matchMedia('(prefers-color-scheme: dark)').matches
    };
  });
  console.log('[Test] Color scheme:', JSON.stringify(colorScheme, null, 2));

  // Test 12: Permissions API
  const perms = await page.evaluate(async () => {
    const results = {};
    for (const name of ['geolocation', 'notifications', 'camera', 'microphone']) {
      try {
        const perm = await navigator.permissions.query({ name });
        results[name] = perm.state;
      } catch (e) {
        results[name] = 'error';
      }
    }
    return results;
  });
  console.log('[Test] Permissions:', JSON.stringify(perms, null, 2));

  await browser.close();
  console.log('[Test] Complete!');
}

testBotDetection().catch(console.error);