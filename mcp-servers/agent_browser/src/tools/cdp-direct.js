/**
 * cdp-direct.js - Raw CDP access MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');
const { notificationManager } = require('../notifications');

/**
 * Send raw CDP command
 */
async function cdpSend(args, context) {
  const { sessionId, domain, method, params, target, frameId } = args;

  const router = getCDPRouter();
  const result = await router.sendCDP(sessionId, domain, method, params, target === 'frame' ? { frameId } : {});

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
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Create a subscription ID
  const subscriptionId = `sub_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const handler = (...eventArgs) => {
    // Send notification via MCP
    notificationManager.sendNotification(sessionId, 'notifications/cdp_event', {
      subscriptionId,
      domain,
      event,
      data: eventArgs[0],
      timestamp: Date.now()
    });
  };

  cdp.on(`${domain}.${event}`, handler);

  // Store handler for cleanup
  const session = router.getSession(sessionId);
  if (!session.eventHandlers) session.eventHandlers = [];
  session.eventHandlers.push({ domain, event, handler, cdp, subscriptionId });

  return {
    success: true,
    subscribed: true,
    subscriptionId,
    domain,
    event
  };
}

/**
 * Unsubscribe from CDP events
 */
async function cdpUnsubscribe(args, context) {
  const { sessionId, subscriptionId } = args;

  const router = getCDPRouter();
  const session = router.getSession(sessionId);

  if (!session.eventHandlers) {
    return { success: false, error: 'No subscriptions found' };
  }

  const index = session.eventHandlers.findIndex(h => h.subscriptionId === subscriptionId);
  if (index === -1) {
    return { success: false, error: 'Subscription not found' };
  }

  const { domain, event, handler, cdp } = session.eventHandlers[index];
  try {
    cdp.off(`${domain}.${event}`, handler);
  } catch (e) {}

  session.eventHandlers.splice(index, 1);

  return { success: true, subscriptionId };
}

// Global capture registry for network/console captures
const captureRegistry = new Map(); // captureId -> { type, entries, handlers, cdp, sessionId }

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
  const captureId = `capture_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

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

  // Store in registry
  captureRegistry.set(captureId, {
    type: 'network',
    entries,
    handlers: { requestHandler, responseHandler },
    cdp,
    sessionId
  });

  return {
    success: true,
    captureId,
    entries: 0
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
  const captureId = `console_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

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

  // Store in registry
  captureRegistry.set(captureId, {
    type: 'console',
    entries,
    handlers: { handler },
    cdp,
    sessionId
  });

  return {
    success: true,
    captureId,
    entries: 0
  };
}

/** Remove a capture's CDP listeners. */
function detachCapture(capture) {
  try {
    if (capture.type === 'network') {
      capture.cdp.off('Network.requestWillBeSent', capture.handlers.requestHandler);
      capture.cdp.off('Network.responseReceived', capture.handlers.responseHandler);
    } else if (capture.type === 'console') {
      capture.cdp.off('Console.messageAdded', capture.handlers.handler);
    }
  } catch (e) {}
}

/**
 * Stop and forget every capture that belongs to a session (called when the
 * session's browser closes). Returns the number of captures stopped.
 */
function stopCapturesForSession(sessionId) {
  let stopped = 0;
  for (const [captureId, capture] of captureRegistry) {
    if (capture.sessionId === sessionId) {
      detachCapture(capture);
      captureRegistry.delete(captureId);
      stopped += 1;
    }
  }
  return stopped;
}

/**
 * Stop a capture and get entries
 */
async function cdpCaptureStop(args, context) {
  const { captureId } = args;

  const capture = captureRegistry.get(captureId);
  if (!capture) {
    return { success: false, error: 'Capture not found' };
  }

  detachCapture(capture);
  const resultEntries = [...capture.entries];
  captureRegistry.delete(captureId);

  return {
    success: true,
    captureId,
    entries: resultEntries,
    count: resultEntries.length
  };
}

/**
 * Get capture entries without stopping
 */
async function cdpCaptureGet(args, context) {
  const { captureId } = args;

  const capture = captureRegistry.get(captureId);
  if (!capture) {
    return { success: false, error: 'Capture not found' };
  }

  return {
    success: true,
    captureId,
    entries: [...capture.entries],
    count: capture.entries.length
  };
}

/**
 * List active captures
 */
async function cdpCaptureList(args, context) {
  const { sessionId } = args;

  const captures = [];
  for (const [id, capture] of captureRegistry) {
    if (!sessionId || capture.sessionId === sessionId) {
      captures.push({
        captureId: id,
        type: capture.type,
        entries: capture.entries.length,
        sessionId: capture.sessionId
      });
    }
  }

  return {
    success: true,
    captures,
    count: captures.length
  };
}

/**
 * Get page metrics (performance, memory, etc.)
 */
async function cdpMetrics(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Get performance metrics (the domain must be enabled first)
  await cdp.send('Performance.enable');
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
  cdpUnsubscribe,
  cdpNetworkCapture,
  cdpConsoleCapture,
  cdpCaptureStop,
  cdpCaptureGet,
  cdpCaptureList,
  cdpMetrics,
  stopCapturesForSession
};