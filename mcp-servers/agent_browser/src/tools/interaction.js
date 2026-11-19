/**
 * interaction.js - Human-like interaction MCP tools
 */

const { getCDPRouter } = require('../cdp-router-wrapper');
const {
  humanMove,
  humanClick,
  humanHover,
  humanDragDrop,
  humanScroll,
  humanDwell,
  calculateTargetPoint
} = require('../human-behavior');

/**
 * Find element and get bounding box
 */
async function findElement(cdp, selector, xpath) {
  if (xpath) {
    const result = await cdp.send('Runtime.evaluate', {
      expression: `
        (function() {
          const xpath = '${xpath.replace(/'/g, "\\'")}';
          const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
          return result.singleNodeValue;
        })()
      `,
      returnByValue: false
    });

    if (!result.result?.objectId) {
      throw new Error(`Element not found for xpath: ${xpath}`);
    }

    const box = await cdp.send('DOM.getBoxModel', { objectId: result.result.objectId });
    return { objectId: result.result.objectId, box: box.model };
  }

  if (selector) {
    const result = await cdp.send('Runtime.evaluate', {
      expression: `
        (function() {
          const el = document.querySelector('${selector.replace(/'/g, "\\'")}');
          return el;
        })()
      `,
      returnByValue: false
    });

    if (!result.result?.objectId) {
      throw new Error(`Element not found for selector: ${selector}`);
    }

    const box = await cdp.send('DOM.getBoxModel', { objectId: result.result.objectId });
    return { objectId: result.result.objectId, box: box.model };
  }

  throw new Error('Either selector or xpath must be provided');
}

/**
 * Click element with human-like movement
 */
async function click(args, context) {
  const {
    sessionId,
    selector,
    xpath,
    position,
    button,
    clickCount,
    modifiers,
    humanize
  } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  let targetPos = position;

  if (!targetPos) {
    const { box } = await findElement(cdp, selector, xpath);
    // Box model returns border box - use content box center
    const contentBox = box.content || box.border;
    const points = contentBox.map(p => ({ x: p.x, y: p.y }));
    const minX = Math.min(...points.map(p => p.x));
    const maxX = Math.max(...points.map(p => p.x));
    const minY = Math.min(...points.map(p => p.y));
    const maxY = Math.max(...points.map(p => p.y));

    targetPos = calculateTargetPoint({
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    });
  }

  // Human-like approach
  let currentPos = { x: 960, y: 540 }; // Default center position
  if (humanize !== false) {
    const moveResult = await humanMove(cdp, targetPos, { persona: args.persona, currentPos });
    currentPos = moveResult.finalPos;
  } else {
    // Direct move
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: targetPos.x,
      y: targetPos.y,
      modifiers: 0,
      button: 'none',
      clickCount: 0
    });
    currentPos = targetPos;
  }

  // Click
  const modMap = { 'Alt': 1, 'Control': 2, 'Meta': 4, 'Shift': 8 };
  const modValue = (modifiers || []).reduce((acc, m) => acc + (modMap[m] || 0), 0);
  const buttonMap = { 'left': 'left', 'right': 'right', 'middle': 'middle' };

  for (let i = 0; i < (clickCount || 1); i++) {
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x: currentPos.x,
      y: currentPos.y,
      modifiers: modValue,
      button: buttonMap[button] || 'left',
      clickCount: i + 1
    });

    await new Promise(r => setTimeout(r, 50 + Math.random() * 50));

    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x: currentPos.x,
      y: currentPos.y,
      modifiers: modValue,
      button: buttonMap[button] || 'left',
      clickCount: i + 1
    });

    if (i < (clickCount || 1) - 1) {
      await new Promise(r => setTimeout(r, 80 + Math.random() * 70));
    }
  }

  return { success: true, target: targetPos };
}

/**
 * Type text with human-like keystrokes
 */
async function type(args, context) {
  const { sessionId, selector, xpath, text, clearFirst, typingSpeed, errorRate, humanize } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Focus element
  if (selector || xpath) {
    const { objectId } = await findElement(cdp, selector, xpath);
    await cdp.send('DOM.focus', { objectId });
  }

  // Clear if requested
  if (clearFirst) {
    await cdp.send('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key: 'a',
      modifiers: 2, // Control
      text: ''
    });
    await cdp.send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: 'a',
      modifiers: 2,
      text: ''
    });
    await new Promise(r => setTimeout(r, 50));
  }

  // Type with human-like timing
  const baseDelay = typingSpeed === 'slow' ? 200 : typingSpeed === 'fast' ? 60 : 120;
  const errRate = errorRate || 0.02;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];

    // Random typo
    if (humanize !== false && Math.random() < errRate && i < text.length - 1) {
      const wrongChar = String.fromCharCode(97 + Math.floor(Math.random() * 26));
      await cdp.send('Input.dispatchKeyEvent', {
        type: 'keyDown',
        key: wrongChar,
        text: wrongChar
      });
      await cdp.send('Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: wrongChar,
        text: ''
      });
      await new Promise(r => setTimeout(r, 80 + Math.random() * 100));

      // Backspace
      await cdp.send('Input.dispatchKeyEvent', {
        type: 'keyDown',
        key: 'Backspace',
        text: ''
      });
      await cdp.send('Input.dispatchKeyEvent', {
        type: 'keyUp',
        key: 'Backspace',
        text: ''
      });
      await new Promise(r => setTimeout(r, 80 + Math.random() * 100));
    }

    // Correct character
    await cdp.send('Input.dispatchKeyEvent', {
      type: 'keyDown',
      key: char,
      text: char
    });
    await cdp.send('Input.dispatchKeyEvent', {
      type: 'keyUp',
      key: char,
      text: ''
    });

    // Variable delay
    const delay = baseDelay + (Math.random() - 0.5) * baseDelay * 0.5;
    await new Promise(r => setTimeout(r, Math.max(20, delay)));
  }

  return { success: true, length: text.length };
}

/**
 * Hover element
 */
async function hover(args, context) {
  const { sessionId, selector, xpath, position, duration, humanize } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  let targetPos = position;

  if (!targetPos) {
    const { box } = await findElement(cdp, selector, xpath);
    const contentBox = box.content || box.border;
    const points = contentBox.map(p => ({ x: p.x, y: p.y }));
    const minX = Math.min(...points.map(p => p.x));
    const maxX = Math.max(...points.map(p => p.x));
    const minY = Math.min(...points.map(p => p.y));
    const maxY = Math.max(...points.map(p => p.y));

    targetPos = calculateTargetPoint({
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY
    });
  }

  let currentPos = { x: 960, y: 540 };
  if (humanize !== false) {
    const hoverResult = await humanHover(cdp, targetPos, { persona: args.persona, duration, currentPos });
    currentPos = hoverResult.finalPos;
  } else {
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: targetPos.x,
      y: targetPos.y,
      modifiers: 0,
      button: 'none',
      clickCount: 0
    });
    currentPos = targetPos;
  }

  // Hold hover
  if (duration) {
    await new Promise(r => setTimeout(r, duration));
  }

  return { success: true, target: targetPos };
}

/**
 * Scroll with human-like behavior
 */
async function scroll(args, context) {
  const { sessionId, direction, distance, selector, humanize } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Get viewport from session config
  const session = router.getSession(sessionId);
  const viewport = session?.emulationConfig?.deviceMetrics || { width: 1920, height: 1080 };

  const scrollConfig = {
    direction: direction || 'down',
    viewportSize: { width: viewport.width, height: viewport.height },
    persona: args.persona
  };

  if (distance) {
    scrollConfig.distance = distance;
  }

  if (selector) {
    scrollConfig.selector = selector;
  }

  if (humanize !== false) {
    const result = await humanScroll(cdp, scrollConfig);
    return { success: true, ...result };
  } else {
    // Direct scroll via wheel
    const deltaY = direction === 'up' ? -(distance || 300) : (distance || 300);
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseWheel',
      x: viewport.width / 2,
      y: viewport.height / 2,
      deltaX: 0,
      deltaY,
      modifiers: 0,
      pointerType: 'mouse'
    });
    return { success: true, distance: distance || 300 };
  }
}

/**
 * Drag and drop
 */
async function dragDrop(args, context) {
  const { sessionId, sourceSelector, sourceXpath, targetSelector, targetXpath, humanize } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  // Find source
  const { box: sourceBox } = await findElement(cdp, sourceSelector, sourceXpath);
  const sourcePoints = (sourceBox.content || sourceBox.border).map(p => ({ x: p.x, y: p.y }));
  const sourcePos = calculateTargetPoint({
    x: Math.min(...sourcePoints.map(p => p.x)),
    y: Math.min(...sourcePoints.map(p => p.y)),
    width: Math.max(...sourcePoints.map(p => p.x)) - Math.min(...sourcePoints.map(p => p.x)),
    height: Math.max(...sourcePoints.map(p => p.y)) - Math.min(...sourcePoints.map(p => p.y))
  });

  // Find target
  const { box: targetBox } = await findElement(cdp, targetSelector, targetXpath);
  const targetPoints = (targetBox.content || targetBox.border).map(p => ({ x: p.x, y: p.y }));
  const targetPos = calculateTargetPoint({
    x: Math.min(...targetPoints.map(p => p.x)),
    y: Math.min(...targetPoints.map(p => p.y)),
    width: Math.max(...targetPoints.map(p => p.x)) - Math.min(...targetPoints.map(p => p.x)),
    height: Math.max(...targetPoints.map(p => p.y)) - Math.min(...targetPoints.map(p => p.y))
  });

  let currentPos = { x: 960, y: 540 };
  if (humanize !== false) {
    const dragResult = await humanDragDrop(cdp, sourcePos, targetPos, { persona: args.persona, currentPos });
    currentPos = dragResult.finalPos;
  } else {
    // Direct drag
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: sourcePos.x, y: sourcePos.y, modifiers: 0, button: 'none', clickCount: 0 });
    await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: sourcePos.x, y: sourcePos.y, modifiers: 0, button: 'left', clickCount: 1 });
    await new Promise(r => setTimeout(r, 100));
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: targetPos.x, y: targetPos.y, modifiers: 0, button: 'left', clickCount: 1 });
    await new Promise(r => setTimeout(r, 100));
    await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: targetPos.x, y: targetPos.y, modifiers: 0, button: 'left', clickCount: 1 });
    currentPos = targetPos;
  }

  return { success: true, source: sourcePos, target: targetPos };
}

/**
 * Key press
 */
async function keyPress(args, context) {
  const { sessionId, key, modifiers, text } = args;

  const router = getCDPRouter();
  const cdp = await router.getPageCDP(sessionId, 'default');

  const modMap = { 'Alt': 1, 'Control': 2, 'Meta': 4, 'Shift': 8 };
  const modValue = (modifiers || []).reduce((acc, m) => acc + (modMap[m] || 0), 0);

  await cdp.send('Input.dispatchKeyEvent', {
    type: 'keyDown',
    key,
    text: text || key,
    modifiers: modValue
  });

  await new Promise(r => setTimeout(r, 30 + Math.random() * 50));

  await cdp.send('Input.dispatchKeyEvent', {
    type: 'keyUp',
    key,
    text: '',
    modifiers: modValue
  });

  return { success: true };
}

module.exports = {
  click,
  type,
  hover,
  scroll,
  dragDrop,
  keyPress
};