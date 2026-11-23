/**
 * extraction.js - Data extraction MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');
const {
  findElement,
  querySelectorExpression,
  querySelectorAllExpression,
  xpathExpression,
  xpathAllExpression
} = require('./dom-utils');

/**
 * Extract data from page
 */
async function extract(args, context) {
  const { sessionId, selector, xpath, attribute, script, multiple, format } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  let expression;

  if (script) {
    // Custom extraction script
    expression = script;
  } else if (xpath) {
    // Always an array so single and multiple results are read the same way.
    expression = multiple ? xpathAllExpression(xpath) : `[${xpathExpression(xpath)}].filter(Boolean)`;
  } else if (selector) {
    expression = multiple
      ? querySelectorAllExpression(selector)
      : `[${querySelectorExpression(selector)}].filter(Boolean)`;
  } else {
    throw new Error('Either selector, xpath, or script must be provided');
  }

  const result = await cdp.send('Runtime.evaluate', {
    expression,
    returnByValue: false,
    awaitPromise: true
  });

  if (!result.result?.objectId) {
    return { success: true, data: null };
  }

  // Extract data based on format
  let data;
  const fmt = format || 'text';

  if (fmt === 'text' || fmt === 'html' || fmt === 'json') {
    // Get properties
    const props = await cdp.send('Runtime.getProperties', {
      objectId: result.result.objectId,
      ownProperties: true
    });

    const elements = [];
    for (const prop of props.result) {
      if (prop.value?.objectId) {
        const desc = await cdp.send('Runtime.callFunctionOn', {
          objectId: prop.value.objectId,
          functionDeclaration: `function() {
            return {
              tagName: this.tagName,
              id: this.id,
              className: this.className,
              textContent: this.textContent,
              innerHTML: this.innerHTML,
              outerHTML: this.outerHTML,
              href: this.href,
              src: this.src,
              alt: this.alt,
              title: this.title,
              value: this.value,
              type: this.type,
              checked: this.checked,
              selected: this.selected
            };
          }`,
          returnByValue: true
        });
        if (desc.result?.value) elements.push(desc.result.value);
      }
    }

    if (fmt === 'text') {
      data = elements.map(e => e.textContent?.trim()).filter(Boolean).join('\n');
    } else if (fmt === 'html') {
      data = elements.map(e => e.outerHTML).join('\n');
    } else {
      data = elements;
    }
  } else if (fmt === 'structured') {
    // Return object IDs for further manipulation
    data = { objectId: result.result.objectId, count: multiple ? 'multiple' : 'single' };
  } else if (fmt === 'markdown') {
    const props = await cdp.send('Runtime.getProperties', { objectId: result.result.objectId, ownProperties: true });
    const elements = [];
    for (const prop of props.result) {
      if (prop.value?.objectId) {
        const desc = await cdp.send('Runtime.callFunctionOn', {
          objectId: prop.value.objectId,
          functionDeclaration: `function() { return { tagName: this.tagName, textContent: this.textContent, href: this.href }; }`,
          returnByValue: true
        });
        if (desc.result?.value) elements.push(desc.result.value);
      }
    }
    data = elements.map(e => {
      if (e.tagName === 'A' && e.href) return `[${e.textContent}](${e.href})`;
      if (e.tagName?.match(/^H[1-6]$/)) return `${'#'.repeat(parseInt(e.tagName[1]))} ${e.textContent}`;
      return e.textContent;
    }).filter(Boolean).join('\n\n');
  }

  return { success: true, data, format: fmt };
}

/**
 * Get element attributes
 */
async function getAttributes(args, context) {
  const { sessionId, selector, xpath, attributes } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const { objectId } = await findElement(cdp, selector, xpath);

  const attrNames = attributes || ['id', 'class', 'href', 'src', 'alt', 'title', 'name', 'value', 'type', 'data-*'];

  const result = await cdp.send('Runtime.callFunctionOn', {
    objectId,
    functionDeclaration: `function(attrs) {
      const result = {};
      for (const attr of attrs) {
        if (attr === 'data-*') {
          for (const a of this.attributes) {
            if (a.name.startsWith('data-')) result[a.name] = a.value;
          }
        } else {
          result[attr] = this.getAttribute(attr);
        }
      }
      return result;
    }`,
    arguments: [{ value: attrNames }],
    returnByValue: true
  });

  return { success: true, attributes: result.result?.value };
}

/**
 * Get full page content
 */
async function getPageContent(args, context) {
  const { sessionId, format } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const fmt = format || 'html';

  if (fmt === 'html') {
    const result = await cdp.send('Runtime.evaluate', {
      expression: `document.documentElement.outerHTML`,
      returnByValue: true
    });
    return { success: true, content: result.result?.value, format: 'html' };
  }

  if (fmt === 'text') {
    const result = await cdp.send('Runtime.evaluate', {
      expression: `document.body.innerText`,
      returnByValue: true
    });
    return { success: true, content: result.result?.value, format: 'text' };
  }

  if (fmt === 'markdown') {
    // Simplified markdown conversion
    const result = await cdp.send('Runtime.evaluate', {
      expression: `
        (function() {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
          const texts = [];
          while (walker.nextNode()) {
            const text = walker.currentNode.textContent.trim();
            if (text) texts.push(text);
          }
          return texts.join('\\n\\n');
        })()
      `,
      returnByValue: true
    });
    return { success: true, content: result.result?.value, format: 'markdown' };
  }

  throw new Error(`Unknown format: ${fmt}`);
}

module.exports = {
  extract,
  getAttributes,
  getPageContent
};