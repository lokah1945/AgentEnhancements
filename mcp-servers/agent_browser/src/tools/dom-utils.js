/**
 * dom-utils.js - Build page-side expressions that look up elements.
 *
 * Selector and XPath strings are embedded with JSON.stringify, which escapes
 * quotes, backslashes and line terminators, so the page receives exactly the
 * string the caller passed and the value can never terminate the literal.
 */

/** JavaScript expression evaluating to the first element matching `selector`. */
function querySelectorExpression(selector) {
  return `document.querySelector(${JSON.stringify(String(selector))})`;
}

/** JavaScript expression evaluating to an array of elements matching `selector`. */
function querySelectorAllExpression(selector) {
  return `Array.from(document.querySelectorAll(${JSON.stringify(String(selector))}))`;
}

/** JavaScript expression evaluating to the first node matching `xpath`. */
function xpathExpression(xpath) {
  return `document.evaluate(${JSON.stringify(String(xpath))}, document, null, ` +
    'XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue';
}

/** JavaScript expression evaluating to an array of nodes matching `xpath`. */
function xpathAllExpression(xpath) {
  return `(function() {
    const result = document.evaluate(${JSON.stringify(String(xpath))}, document, null,
      XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
    const nodes = [];
    for (let i = 0; i < result.snapshotLength; i++) nodes.push(result.snapshotItem(i));
    return nodes;
  })()`;
}

/**
 * Resolve an element by XPath (preferred when both are given) or CSS selector
 * and return its remote objectId, plus its box model when `withBox` is set.
 */
async function findElement(cdp, selector, xpath, { withBox = false } = {}) {
  let expression;
  let description;
  if (xpath) {
    expression = xpathExpression(xpath);
    description = `xpath: ${xpath}`;
  } else if (selector) {
    expression = querySelectorExpression(selector);
    description = `selector: ${selector}`;
  } else {
    throw new Error('Either selector or xpath must be provided');
  }

  const result = await cdp.send('Runtime.evaluate', { expression, returnByValue: false });
  if (result.exceptionDetails) {
    const detail = result.exceptionDetails.exception && result.exceptionDetails.exception.description;
    throw new Error(`Invalid ${description}: ${detail || result.exceptionDetails.text}`);
  }
  const objectId = result.result && result.result.objectId;
  if (!objectId) {
    throw new Error(`Element not found for ${description}`);
  }
  if (!withBox) return { objectId };
  const box = await cdp.send('DOM.getBoxModel', { objectId });
  return { objectId, box: box.model };
}

module.exports = {
  querySelectorExpression,
  querySelectorAllExpression,
  xpathExpression,
  xpathAllExpression,
  findElement
};
