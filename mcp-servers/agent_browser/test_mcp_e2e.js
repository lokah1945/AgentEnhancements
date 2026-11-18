const { chromium } = require('playwright');
const { buildLaunchArgs, applyCDPEmulation, buildCDPEmulationConfig } = require('./src/launch-config');
const { SessionManager } = require('./src/session-manager');
const { CDPRouter } = require('./src/cdp-router');
const { initializeBrowser, getPageCDP, closeBrowser } = require('./src/cdp-router-wrapper');

async function testMCPTools() {
  console.log('[MCP Test] Testing session_create (persistent)...');
  
  const mgr = new SessionManager();
  const session = await mgr.createSession({ persistent: true });
  console.log('[MCP Test] Session created:', session.sessionId);
  
  console.log('[MCP Test] Initializing browser...');
  await initializeBrowser(session.sessionId);
  
  console.log('[MCP Test] Testing navigate...');
  const cdp = await getPageCDP(session.sessionId, 'default');
  await cdp.send('Page.navigate', { url: 'https://example.com' });
  
  // Wait for load using event
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Navigation timeout')), 30000);
    cdp.once('Page.loadEventFired', () => {
      clearTimeout(timeout);
      resolve();
    });
  });
  
  const title = await cdp.send('Runtime.evaluate', {
    expression: 'document.title',
    returnByValue: true
  });
  console.log('[MCP Test] Page title:', title.result.value);
  
  console.log('[MCP Test] Testing extract...');
  const extract = await cdp.send('Runtime.evaluate', {
    expression: "document.querySelector('h1').textContent",
    returnByValue: true
  });
  console.log('[MCP Test] Extracted:', extract.result.value);
  
  console.log('[MCP Test] Testing screenshot...');
  const screenshot = await cdp.send('Page.captureScreenshot', { format: 'png' });
  console.log('[MCP Test] Screenshot size:', screenshot.data.length, 'chars base64');
  
  console.log('[MCP Test] Testing cdp_evaluate...');
  const evalResult = await cdp.send('Runtime.evaluate', {
    expression: 'navigator.userAgent',
    returnByValue: true
  });
  console.log('[MCP Test] UA from CDP:', evalResult.result.value.substring(0, 50) + '...');
  
  console.log('[MCP Test] Testing tab_new...');
  const { createPage } = require('./src/cdp-router-wrapper');
  const newPage = await createPage(session.sessionId, 'https://httpbin.org/html');
  console.log('[MCP Test] New tab created:', newPage.pageId);
  
  await closeBrowser(session.sessionId);
  console.log('[MCP Test] All MCP tools working!');
}

testMCPTools().catch(e => {
  console.error('[MCP Test] Error:', e.message);
  process.exit(1);
});
