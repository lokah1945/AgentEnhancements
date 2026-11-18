/**
 * observation.js - Screenshot, PDF, DOM snapshot MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');

/**
 * Take screenshot via CDP
 */
async function screenshot(args, context) {
  const { sessionId, selector, xpath, fullPage, format, quality, clip, omitBackground } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  let screenshotOptions = {
    format: format || 'png',
    quality: quality || 90,
    fromSurface: true,
    captureBeyondViewport: fullPage || false
  };

  if (omitBackground) {
    screenshotOptions.captureBeyondViewport = false;
    screenshotOptions.format = 'png'; // PNG supports transparency
  }

  if (clip) {
    screenshotOptions.clip = {
      x: clip.x || 0,
      y: clip.y || 0,
      width: clip.width || 1920,
      height: clip.height || 1080,
      scale: clip.scale || 1
    };
  }

  if (selector || xpath) {
    // Element screenshot
    let elementResult;

    if (xpath) {
      elementResult = await cdp.send('Runtime.evaluate', {
        expression: `document.evaluate('${xpath.replace(/'/g, "\\'")}', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue`,
        returnByValue: false
      });
    } else {
      elementResult = await cdp.send('Runtime.evaluate', {
        expression: `document.querySelector('${selector.replace(/'/g, "\\'")}')`,
        returnByValue: false
      });
    }

    if (!elementResult.result?.objectId) {
      throw new Error('Element not found for screenshot');
    }

    // Get element box model
    const boxModel = await cdp.send('DOM.getBoxModel', { objectId: elementResult.result.objectId });
    const contentBox = boxModel.model.content || boxModel.model.border;
    const points = contentBox.map(p => ({ x: p.x, y: p.y }));
    const minX = Math.min(...points.map(p => p.x));
    const minY = Math.min(...points.map(p => p.y));
    const maxX = Math.max(...points.map(p => p.x));
    const maxY = Math.max(...points.map(p => p.y));

    screenshotOptions.clip = {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
      scale: 1
    };
  }

  const result = await cdp.send('Page.captureScreenshot', screenshotOptions);

  return {
    success: true,
    data: result.data, // Base64 encoded
    format: format || 'png',
    mimeType: format === 'jpeg' ? 'image/jpeg' : 'image/png'
  };
}

/**
 * Generate PDF via CDP
 */
async function pdf(args, context) {
  const { sessionId, format, printBackground, landscape, margin, scale, paperWidth, paperHeight } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const paperFormats = {
    'A4': { width: 8.27, height: 11.69 },
    'Letter': { width: 8.5, height: 11 },
    'Legal': { width: 8.5, height: 14 }
  };

  const paper = paperFormats[format || 'A4'] || { width: 8.27, height: 11.69 };

  const pdfOptions = {
    landscape: landscape || false,
    printBackground: printBackground !== false,
    paperWidth: paperWidth || paper.width,
    paperHeight: paperHeight || paper.height,
    marginTop: margin?.top ? parseFloat(margin.top) / 72 : 0.4,
    marginBottom: margin?.bottom ? parseFloat(margin.bottom) / 72 : 0.4,
    marginLeft: margin?.left ? parseFloat(margin.left) / 72 : 0.4,
    marginRight: margin?.right ? parseFloat(margin.right) / 72 : 0.4,
    scale: scale || 1,
    preferCSSPageSize: true
  };

  const result = await cdp.send('Page.printToPDF', pdfOptions);

  return {
    success: true,
    data: result.data, // Base64 encoded
    format: 'pdf',
    mimeType: 'application/pdf'
  };
}

/**
 * Capture full DOM snapshot via CDP DOMSnapshot
 */
async function domSnapshot(args, context) {
  const { sessionId, includeStyles, includePaintOrder } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const snapshot = await cdp.send('DOMSnapshot.captureSnapshot', {
    computedStyles: includeStyles ? ['*'] : [],
    includePaintOrder: includePaintOrder || false,
    includeUserAgentShadowTree: true
  });

  return {
    success: true,
    snapshot: {
      documents: snapshot.documents,
      strings: snapshot.strings,
      computedStyles: snapshot.computedStyles,
      layoutTreeNodes: snapshot.layoutTreeNodes
    }
  };
}

/**
 * Get page HTML
 */
async function getHTML(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const result = await cdp.send('Runtime.evaluate', {
    expression: 'document.documentElement.outerHTML',
    returnByValue: true
  });

  return {
    success: true,
    html: result.result?.value
  };
}

/**
 * Get page text content
 */
async function getText(args, context) {
  const { sessionId } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const result = await cdp.send('Runtime.evaluate', {
    expression: 'document.body.innerText',
    returnByValue: true
  });

  return {
    success: true,
    text: result.result?.value
  };
}

module.exports = {
  screenshot,
  pdf,
  domSnapshot,
  getHTML,
  getText
};