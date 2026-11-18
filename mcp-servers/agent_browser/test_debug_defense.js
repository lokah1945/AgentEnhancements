const { chromium } = require('playwright');
const { buildLaunchArgs, applyCDPEmulation, buildCDPEmulationConfig, applyHeadlessDefense } = require('./src/launch-config');
const { SessionManager } = require('./src/session-manager');
const { initializeBrowser, getPageCDP, closeBrowser } = require('./src/cdp-router-wrapper');

async function testDebugDefense() {
  console.log('[Test] Creating persistent session...');
  
  const mgr = new SessionManager();
  const session = await mgr.createSession({ persistent: true });
  console.log('[Test] Session:', session.sessionId);
  
  console.log('[Test] Initializing browser...');
  await initializeBrowser(session.sessionId);
  
  const cdp = await getPageCDP(session.sessionId, 'default');
  
  // Test defense script BEFORE navigation
  console.log('[Test] Checking defense script execution on about:blank...');
  const beforeNav = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        return {
          chrome: !!window.chrome,
          chromeRuntime: !!window.chrome?.runtime,
          plugins: navigator.plugins?.length || 0,
          mimeTypes: navigator.mimeTypes?.length || 0,
          platform: navigator.platform,
          vendorSub: navigator.vendorSub,
          productSub: navigator.productSub,
          defenseApplied: window.__agentBrowserHeadlessDefenseApplied
        };
      })()
    `,
    returnByValue: true
  });
  console.log('[Test] Before navigation:', JSON.stringify(beforeNav.result.value, null, 2));
  
  console.log('[Test] Navigating to google.com...');
  await cdp.send('Page.navigate', { url: 'https://www.google.com' });
  
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Navigation timeout')), 30000);
    cdp.once('Page.loadEventFired', () => {
      clearTimeout(timeout);
      resolve();
    });
  });
  
  await new Promise(r => setTimeout(r, 2000));
  
  console.log('[Test] Checking after navigation...');
  const afterNav = await cdp.send('Runtime.evaluate', {
    expression: `
      (function() {
        return {
          chrome: !!window.chrome,
          chromeRuntime: !!window.chrome?.runtime,
          plugins: navigator.plugins?.length || 0,
          mimeTypes: navigator.mimeTypes?.length || 0,
          platform: navigator.platform,
          vendorSub: navigator.vendorSub,
          productSub: navigator.productSub,
          defenseApplied: window.__agentBrowserHeadlessDefenseApplied,
          // Check if our mock plugins exist
          pluginNames: Array.from(navigator.plugins || []).map(p => p.name),
          mimeTypesList: Array.from(navigator.mimeTypes || []).map(m => m.type)
        };
      })()
    `,
    returnByValue: true
  });
  console.log('[Test] After navigation:', JSON.stringify(afterNav.result.value, null, 2));
  
  await closeBrowser(session.sessionId);
  console.log('[Test] Complete!');
}

testDebugDefense().catch(e => {
  console.error('[Test] Error:', e.message, e.stack);
  process.exit(1);
});
