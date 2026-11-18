const { chromium } = require('playwright');
const { buildLaunchArgs, applyCDPEmulation, buildCDPEmulationConfig } = require('./src/launch-config');
const { SessionManager } = require('./src/session-manager');
const { initializeBrowser, getPageCDP, closeBrowser } = require('./src/cdp-router-wrapper');

async function testGoogleCaptcha() {
  console.log('[Test] Creating persistent session...');
  
  const mgr = new SessionManager();
  const session = await mgr.createSession({ persistent: true });
  console.log('[Test] Session:', session.sessionId);
  
  console.log('[Test] Initializing browser...');
  await initializeBrowser(session.sessionId);
  
  const cdp = await getPageCDP(session.sessionId, 'default');
  
  console.log('[Test] Navigating to google.com...');
  await cdp.send('Page.navigate', { url: 'https://www.google.com' });
  
  // Wait for load
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Navigation timeout')), 30000);
    cdp.once('Page.loadEventFired', () => {
      clearTimeout(timeout);
      resolve();
    });
  });
  
  console.log('[Test] Page loaded, checking for CAPTCHA/bot detection...');
  
  // Wait a bit for any dynamic content
  await new Promise(r => setTimeout(r, 3000));
  
  // Check page content for CAPTCHA indicators
  const pageContent = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        const bodyText = document.body.innerText.toLowerCase();
        const html = document.documentElement.outerHTML.toLowerCase();
        
        return {
          title: document.title,
          url: window.location.href,
          hasCaptcha: bodyText.includes('captcha') || bodyText.includes('unusual traffic') || bodyText.includes('verify you') || bodyText.includes('robot') || bodyText.includes('blocked'),
          hasRecaptcha: html.includes('recaptcha') || html.includes('g-recaptcha') || html.includes('h-captcha'),
          hasCloudflare: html.includes('cloudflare') || html.includes('cf-ray') || html.includes('__cf_'),
          bodyTextPreview: bodyText.substring(0, 500),
          forms: document.forms.length,
          scripts: document.scripts.length,
          iframes: document.querySelectorAll('iframe').length
        };
      })()
    `,
    returnByValue: true
  });
  
  console.log('[Test] Page analysis:', JSON.stringify(pageContent.result.value, null, 2));
  
  // Check navigator properties again on Google
  const navCheck = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        return {
          webdriver: navigator.webdriver,
          chrome: !!window.chrome,
          chromeRuntime: !!window.chrome?.runtime,
          plugins: navigator.plugins.length,
          mimeTypes: navigator.mimeTypes.length,
          permissions: navigator.permissions ? 'exists' : 'missing',
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          hardwareConcurrency: navigator.hardwareConcurrency,
          deviceMemory: navigator.deviceMemory,
          maxTouchPoints: navigator.maxTouchPoints,
          vendor: navigator.vendor,
          vendorSub: navigator.vendorSub,
          product: navigator.product,
          productSub: navigator.productSub
        };
      })()
    `,
    returnByValue: true
  });
  
  console.log('[Test] Navigator check on Google:', JSON.stringify(navCheck.result.value, null, 2));
  
  // Check for bot detection scripts
  const scriptCheck = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        const scripts = Array.from(document.scripts).map(s => s.src || s.innerHTML.substring(0, 200));
        const botScripts = scripts.filter(s => 
          s.includes('bot') || s.includes('captcha') || s.includes('recaptcha') || 
          s.includes('datadome') || s.includes('perimeterx') || s.includes('akamai') ||
          s.includes('cloudflare') || s.includes('distil') || s.includes('shape') ||
          s.includes('fingerprint') || s.includes('threatmetrix') || s.includes('arkose')
        );
        return { totalScripts: scripts.length, botScripts: botScripts.length, botScriptUrls: botScripts };
      })()
    `,
    returnByValue: true
  });
  
  console.log('[Test] Script analysis:', JSON.stringify(scriptCheck.result.value, null, 2));
  
  // Check network requests for bot detection endpoints
  const networkCheck = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        // Check if there are any pending XHR/fetch to known bot detection domains
        return { note: 'Would need Network domain to check actual requests' };
      })()
    `,
    returnByValue: true
  });
  
  console.log('[Test] Network check:', JSON.stringify(networkCheck.result.value, null, 2));
  
  // Take screenshot for visual verification
  const screenshot = await cdp.send('Page.captureScreenshot', { format: 'png', fullPage: true });
  const fs = require('fs');
  fs.writeFileSync('/tmp/google_test.png', Buffer.from(screenshot.data, 'base64'));
  console.log('[Test] Screenshot saved to /tmp/google_test.png');
  
  await closeBrowser(session.sessionId);
  console.log('[Test] Complete!');
}

testGoogleCaptcha().catch(e => {
  console.error('[Test] Error:', e.message, e.stack);
  process.exit(1);
});
