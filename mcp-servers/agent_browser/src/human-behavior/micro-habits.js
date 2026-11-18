/**
 * micro-habits.js - Human micro-behaviors (idle fidget, tab hover, etc.)
 * Ported from QTEProject HumanLike_MicroHabits.js (no spoofing)
 */

'use strict';

const {
  gaussianRandom,
  clamp,
  getRandomInt,
  sleep,
  trackedRandom,
  distance
} = require('./math-utils');

/**
 * Execute idle fidget behavior (mouse drift, small movements)
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config - Fidget config
 */
async function idleFidget(cdp, config) {
  const {
    viewportSize = { width: 1920, height: 1080 },
    persona = {},
    currentPos = { x: viewportSize.width * 0.5, y: viewportSize.height * 0.5 }
  } = config;

  const fidgetType = selectFidgetType(persona);

  switch (fidgetType) {
    case 'mouseDrift':
      await mouseDrift(cdp, { viewportSize, persona, currentPos });
      break;
    case 'microScroll':
      await microScroll(cdp, { viewportSize, persona });
      break;
    case 'windowResize':
      await simulateWindowResize(cdp, { viewportSize, persona });
      break;
    case 'tabHover':
      await tabBarHover(cdp, { viewportSize, persona });
      break;
  }
}

/**
 * Select fidget type based on persona weights
 */
function selectFidgetType(persona) {
  const weights = persona.idle?.fidgetWeights || {
    mouseDrift: 0.5,
    microScroll: 0.2,
    windowResize: 0.1,
    tabHover: 0.2
  };

  const rand = trackedRandom();
  let cum = 0;
  for (const [type, weight] of Object.entries(weights)) {
    cum += weight;
    if (rand <= cum) return type;
  }
  return 'mouseDrift';
}

/**
 * Mouse drift - slow wandering near current position
 */
async function mouseDrift(cdp, config) {
  const {
    viewportSize = { width: 1920, height: 1080 },
    persona = {},
    currentPos
  } = config;

  const steps = getRandomInt(8, 20);
  const driftRadius = persona.idle?.driftRadius || 30;

  for (let i = 0; i < steps; i++) {
    const angle = trackedRandom() * 2 * Math.PI;
    const radius = trackedRandom() * driftRadius;

    const targetX = clamp(
      Math.round(currentPos.x + Math.cos(angle) * radius),
      0, viewportSize.width
    );
    const targetY = clamp(
      Math.round(currentPos.y + Math.sin(angle) * radius),
      0, viewportSize.height
    );

    // Slow, lazy movement
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: targetX,
      y: targetY,
      modifiers: 0,
      button: 'none',
      clickCount: 0
    });

    currentPos.x = targetX;
    currentPos.y = targetY;

    await sleep(getRandomInt(200, 800)); // Slow drift
  }
}

/**
 * Micro scroll - tiny scroll adjustments
 */
async function microScroll(cdp, config) {
  const { viewportSize = { width: 1920, height: 1080 }, persona = {} } = config;

  const steps = getRandomInt(1, 3);
  for (let i = 0; i < steps; i++) {
    const deltaX = gaussianRandom(0, 3);
    const deltaY = gaussianRandom(0, 5);

    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseWheel',
      x: viewportSize.width / 2,
      y: viewportSize.height / 2,
      deltaX: Math.round(deltaX),
      deltaY: Math.round(deltaY),
      modifiers: 0,
      pointerType: 'mouse'
    });

    await sleep(getRandomInt(100, 400));
  }
}

/**
 * Simulate window resize (via CDP Emulation.setDeviceMetricsOverride)
 */
async function simulateWindowResize(cdp, config) {
  const { viewportSize = { width: 1920, height: 1080 }, persona = {} } = config;

  // Small random resize (±5%)
  const newWidth = Math.round(viewportSize.width * (0.95 + trackedRandom() * 0.1));
  const newHeight = Math.round(viewportSize.height * (0.95 + trackedRandom() * 0.1));

  try {
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: newWidth,
      height: newHeight,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: newWidth,
      screenHeight: newHeight
    });

    // Restore after brief moment
    await sleep(getRandomInt(500, 2000));

    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: viewportSize.width,
      height: viewportSize.height,
      deviceScaleFactor: 1,
      mobile: false,
      screenWidth: viewportSize.width,
      screenHeight: viewportSize.height
    });
  } catch (e) {
    console.warn('[MicroHabits] Window resize failed:', e.message);
  }
}

/**
 * Tab bar hover - move mouse to tab area briefly
 */
async function tabBarHover(cdp, config) {
  const { viewportSize = { width: 1920, height: 1080 }, persona = {} } = config;

  // Tab bar is typically at top (y: 0-40)
  const tabY = getRandomInt(5, 35);
  const tabX = getRandomInt(100, viewportSize.width - 100);

  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: tabX,
    y: tabY,
    modifiers: 0,
    button: 'none',
    clickCount: 0
  });

  await sleep(getRandomInt(500, 1500));

  // Return to content area
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: viewportSize.width * 0.5,
    y: viewportSize.height * 0.5,
    modifiers: 0,
    button: 'none',
    clickCount: 0
  });
}

/**
 * Pre-click sequence (approach, pause, click)
 * @param {CDPSession} cdp - CDP session
 * @param {{x:number,y:number}} target - Click target
 * @param {Object} persona - Persona config
 */
async function preClickSequence(cdp, target, persona) {
  // Approach with human movement
  await humanApproach(cdp, target, persona);

  // Pre-click pause (dwell on target)
  const pauseTime = getHumanDelay(
    persona.click?.preClickPause || 150,
    persona.click?.preClickVariance || 0.3
  );
  await sleep(pauseTime);

  // Micro-adjustment (settle)
  for (let i = 0; i < 2; i++) {
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: target.x + gaussianRandom(0, 0.5),
      y: target.y + gaussianRandom(0, 0.5),
      modifiers: 0,
      button: 'none',
      clickCount: 0
    });
    await sleep(getRandomInt(20, 50));
  }
}

/**
 * Human approach to target (re-export from mouse-physics)
 */
const { humanMove } = require('./mouse-physics');
async function humanApproach(cdp, target, persona) {
  return humanMove(cdp, target, { persona });
}

/**
 * Post-click behavior
 * @param {CDPSession} cdp - CDP session
 * @param {Object} persona - Persona config
 */
async function postClickBehavior(cdp, persona) {
  const action = trackedRandom() < 0.7 ? 'stay' : 'fidget';

  if (action === 'fidget') {
    await idleFidget(cdp, { persona });
  } else {
    // Stay - small settle movement
    await sleep(getRandomInt(100, 300));
  }
}

/**
 * Reading behavior - scroll, dwell, scan pattern
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config - Reading config
 */
async function readingBehavior(cdp, config) {
  const {
    persona = {},
    duration = 30000, // 30 seconds default
    viewportSize = { width: 1920, height: 1080 }
  } = config;

  const { humanScroll, humanDwell } = require('./scroll-markov');

  const startTime = Date.now();
  let state = 'scan';

  while (Date.now() - startTime < duration) {
    switch (state) {
      case 'scan':
        // Fast scan scroll
        await humanScroll(cdp, {
          direction: 'down',
          distance: 400 + trackedRandom() * 300,
          viewportSize,
          persona
        });
        state = trackedRandom() < 0.3 ? 'read' : 'scan';
        break;

      case 'read':
        // Dwell for reading
        await humanDwell(cdp, { persona });
        state = trackedRandom() < 0.4 ? 'scan' : trackedRandom() < 0.7 ? 'read' : 'scan';
        break;

      case 'fidget':
        await idleFidget(cdp, { viewportSize, persona });
        state = 'read';
        break;
    }

    // Random fidget chance
    if (trackedRandom() < (persona.idle?.fidgetChance || 0.1)) {
      await idleFidget(cdp, { viewportSize, persona });
    }
  }
}

/**
 * Page orientation behavior (initial scan on page load)
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config
 */
async function pageOrientation(cdp, config) {
  const { viewportSize = { width: 1920, height: 1080 }, persona = {} } = config;

  // Quick scan: scroll down a bit, then back up
  await humanScroll(cdp, {
    direction: 'down',
    distance: 200 + trackedRandom() * 300,
    viewportSize,
    persona
  });

  await sleep(getRandomInt(500, 1500));

  // Scroll back up slightly
  await humanScroll(cdp, {
    direction: 'up',
    distance: 100 + trackedRandom() * 150,
    viewportSize,
    persona
  });

  // Final position in upper content area
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: viewportSize.width * (0.3 + trackedRandom() * 0.4),
    y: viewportSize.height * (0.2 + trackedRandom() * 0.3),
    modifiers: 0,
    button: 'none',
    clickCount: 0
  });
}

module.exports = {
  idleFidget,
  preClickSequence,
  postClickBehavior,
  readingBehavior,
  pageOrientation,
  humanApproach,
  mouseDrift,
  microScroll,
  simulateWindowResize,
  tabBarHover
};