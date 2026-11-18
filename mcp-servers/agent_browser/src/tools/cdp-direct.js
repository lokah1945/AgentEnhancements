/**
 * cdp-direct.js - Raw CDP access MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');

/**
 * Send raw CDP command
 */
async function cdpSend(args, context) {
  const { sessionId, domain, method, params, target, frameId } = args;

  const router = getCDPRouter();
  const result = await router.sendCDP(sessionId, domain, method, params, { target, frameId });

  return {
    success: true,
    result
  };
}

/**
 * Evaluate JavaScript in page context
 */
async function cdpEvaluate(args, context) {
  const { sessionId, expression, awaitPromise, returnByValue, target, frameId } = args;

  const router = getCDPRouter();
  const value = await router.evaluate(sessionId, expression, {
    awaitPromise: awaitPromise !== false,
    returnByValue: returnByValue !== false,
    target,
    frameId
  });

  return {
    success: true,
    value
  };
}

/**
 * Subscribe to CDP events
 */
async function cdpSubscribe(args, context) {
  const { sessionId, domain, event, filter } = args;

  const router = getCDPRouter();

  // This would need a notification system for MCP
  // For now, return subscription info
  await router.subscribe(sessionId, domain, event, filter);

  return {
    success: true,
    subscribed: true,
    domain,
    event
  };
}

/**
 * Capture network traffic
 */
async function cdpNetworkCapture(args, context) {
  const { sessionId, filter, maxEntries, includeBody } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Enable network domain
  await cdp.send('Network.enable');

  const entries = [];
  const max = maxEntries || 500;

  // Set up listeners
  const requestHandler = (params) => {
    if (entries.length >= max) return;

    const req = params.request;
    if (filter) {
      if (filter.urlPattern && !req.url.includes(filter.urlPattern)) return;
      if (filter.method && req.method !== filter.method) return;
      if (filter.resourceType && req.resourceType !== filter.resourceType) return;
    }

    entries.push({
      type: 'request',
      requestId: params.requestId,
      url: req.url,
      method: req.method,
      headers: req.headers,
      resourceType: req.resourceType,
      timestamp: params.timestamp,
      timestampMonotonic: Date.now()
    });
  };

  const responseHandler = async (params) => {
    if (entries.length >= max) return;

    const resp = params.response;
    if (filter) {
      if (filter.urlPattern && !resp.url.includes(filter.urlPattern)) return;
    }

    let body = null;
    if (includeBody !== false) {
      try {
        const bodyResult = await cdp.send('Network.getResponseBody', { requestId: params.requestId });
        body = bodyResult.body;
        if (bodyResult.base64Encoded) {
          body = Buffer.from(body, 'base64').toString('utf8');
        }
      } catch (e) {
        body = { error: e.message };
      }
    }

    entries.push({
      type: 'response',
      requestId: params.requestId,
      url: resp.url,
      status: resp.status,
      statusText: resp.statusText,
      headers: resp.headers,
      mimeType: resp.mimeType,
      body,
      timestamp: params.timestamp,
      timestampMonotonic: Date.now()
    });
  };

  cdp.on('Network.requestWillBeSent', requestHandler);
  cdp.on('Network.responseReceived', responseHandler);

  // Return a function to stop capture (in real implementation, this would be async)
  return {
    success: true,
    captureId: `capture_${Date.now()}`,
    stopCapture: () => {
      cdp.off('Network.requestWillBeSent', requestHandler);
      cdp.off('Network.responseReceived', responseHandler);
      return { entries };
    }
  };
}

/**
 * Capture console messages
 */
async function cdpConsoleCapture(args, context) {
  const { sessionId, maxEntries } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  await cdp.send('Console.enable');

  const entries = [];
  const max = maxEntries || 200;

  const handler = (params) => {
    if (entries.length >= max) return;

    entries.push({
      type: params.type,
      text: params.args?.map(a => a.value).join(' ') || '',
      args: params.args?.map(a => ({ type: a.type, value: a.value })) || [],
      stackTrace: params.stackTrace,
      timestamp: params.timestamp,
      timestampMonotonic: Date.now()
    });
  };

  cdp.on('Console.messageAdded', handler);

  return {
    success: true,
    captureId: `console_${Date.now()}`,
    stopCapture: () => {
      cdp.off('Console.messageAdded', handler);
      return { entries };
    }
  };
}

/**
 * Get page metrics (performance, memory, etc.)
 */
async function cdpMetrics(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Get performance metrics
  const metrics = await cdp.send('Performance.getMetrics');

  // Get memory info
  let memory = null;
  try {
    memory = await cdp.send('Runtime.evaluate', {
      expression: `({
        jsHeapSizeLimit: performance.memory?.jsHeapSizeLimit,
        totalJSHeapSize: performance.memory?.totalJSHeapSize,
        usedJSHeapSize: performance.memory?.usedJSHeapSize
      })`,
      returnByValue: true
    });
  } catch (e) {}

  // Get navigation timing
  const navigation = await cdp.send('Runtime.evaluate', {
    expression: `({
      navigationStart: performance.timing?.navigationStart,
      loadEventEnd: performance.timing?.loadEventEnd,
      domContentLoadedEventEnd: performance.timing?.domContentLoadedEventEnd,
      connectEnd: performance.timing?.connectEnd,
      responseEnd: performance.timing?.responseEnd
    })`,
    returnByValue: true
  });

  return {
    success: true,
    metrics: metrics.metrics,
    memory: memory?.result?.value,
    navigation: navigation?.result?.value
  };
}

module.exports = {
  cdpSend,
  cdpEvaluate,
  cdpSubscribe,
  cdpNetworkCapture,
  cdpConsoleCapture,
  cdpMetrics
};