/**
 * scroll-markov.js - Human-like scrolling using CTMC + Weibull dwell
 * Ported from QTEProject HumanLike_ScrollMarkov.js (no spoofing)
 */

'use strict';

const {
  gaussianRandom,
  clamp,
  getRandomInt,
  sleep,
  trackedRandom,
  getHumanDelay
} = require('./math-utils');

/**
 * Scroll direction enum
 */
const ScrollDirection = {
  DOWN: 'down',
  UP: 'up',
  LEFT: 'left',
  RIGHT: 'right'
};

/**
 * CTMC States for scroll behavior
 */
const ScrollState = {
  READING: 'reading',      // Dwelling, not scrolling
  SCANNING: 'scanning',    // Fast scroll, looking for content
  SCROLLING: 'scrolling',  // Normal reading scroll
  PAUSED: 'paused',        // Brief pause mid-scroll
  FIDGET: 'fidget'         // Micro-scroll adjustments
};

/**
 * Transition probability matrix (persona-dependent)
 * Rows: from state, Cols: to state
 */
const DEFAULT_TRANSITIONS = {
  [ScrollState.READING]: {
    [ScrollState.READING]: 0.60,
    [ScrollState.SCANNING]: 0.10,
    [ScrollState.SCROLLING]: 0.20,
    [ScrollState.PAUSED]: 0.05,
    [ScrollState.FIDGET]: 0.05
  },
  [ScrollState.SCANNING]: {
    [ScrollState.READING]: 0.30,
    [ScrollState.SCANNING]: 0.40,
    [ScrollState.SCROLLING]: 0.20,
    [ScrollState.PAUSED]: 0.05,
    [ScrollState.FIDGET]: 0.05
  },
  [ScrollState.SCROLLING]: {
    [ScrollState.READING]: 0.25,
    [ScrollState.SCANNING]: 0.10,
    [ScrollState.SCROLLING]: 0.50,
    [ScrollState.PAUSED]: 0.10,
    [ScrollState.FIDGET]: 0.05
  },
  [ScrollState.PAUSED]: {
    [ScrollState.READING]: 0.40,
    [ScrollState.SCANNING]: 0.10,
    [ScrollState.SCROLLING]: 0.30,
    [ScrollState.PAUSED]: 0.15,
    [ScrollState.FIDGET]: 0.05
  },
  [ScrollState.FIDGET]: {
    [ScrollState.READING]: 0.50,
    [ScrollState.SCANNING]: 0.05,
    [ScrollState.SCROLLING]: 0.20,
    [ScrollState.PAUSED]: 0.15,
    [ScrollState.FIDGET]: 0.10
  }
};

/**
 * Weibull distribution for dwell time (reading pauses)
 * Shape < 1 = decreasing hazard (long reads more likely)
 * Shape > 1 = increasing hazard (short reads more likely)
 * @param {number} shape - Weibull shape parameter
 * @param {number} scale - Weibull scale parameter (ms)
 * @returns {number} Sampled dwell time in ms
 */
function sampleWeibullDwell(shape = 0.8, scale = 3000) {
  const u = Math.random();
  return scale * Math.pow(-Math.log(1 - u), 1 / shape);
}

/**
 * Scroll distance distribution (log-normal for natural variation)
 * @param {number} meanPx - Mean scroll distance
 * @param {number} stdDev - Standard deviation factor
 * @returns {number} Scroll distance in pixels
 */
function sampleScrollDistance(meanPx = 300, stdDev = 0.5) {
  // Log-normal: exp(N(ln(mean) - 0.5*sigma^2, sigma))
  const sigma = stdDev;
  const mu = Math.log(meanPx) - 0.5 * sigma * sigma;
  return Math.exp(gaussianRandom(mu, sigma));
}

/**
 * Scroll velocity profile (ease-in-out with variance)
 * @param {number} progress - 0 to 1
 * @param {number} variance - Variance factor
 * @returns {number} Velocity multiplier
 */
function scrollVelocityProfile(progress, variance = 0.2) {
  // Sine ease-in-out with noise
  const base = Math.sin(Math.PI * progress);
  const noise = 1 + gaussianRandom(0, variance);
  return clamp(base * noise, 0.1, 1.5);
}

/**
 * Generate scroll steps for a scroll action
 * @param {Object} config - Scroll configuration
 * @returns {Array<{dx:number, dy:number, delay:number}>}
 */
function generateScrollSteps(config) {
  const {
    direction = ScrollDirection.DOWN,
    distance = 300,
    viewportSize = { width: 1920, height: 1080 },
    persona = {}
  } = config;

  const steps = [];
  const stepCount = clamp(Math.round(distance / 50), 5, 30);
  const baseDelay = getHumanDelay(16, 0.3); // ~60fps base

  // Determine scroll delta per step
  const totalDelta = direction === ScrollDirection.UP ? -distance : distance;
  const deltaPerStep = totalDelta / stepCount;

  for (let i = 1; i <= stepCount; i++) {
    const progress = i / stepCount;
    const velocity = scrollVelocityProfile(progress);
    const stepDelta = deltaPerStep * velocity;

    // Add micro-variance
    const variance = stepDelta * 0.1 * gaussianRandom(0, 1);

    let dx = 0, dy = 0;
    if (direction === ScrollDirection.LEFT || direction === ScrollDirection.RIGHT) {
      dx = direction === ScrollDirection.LEFT ? stepDelta + variance : -(stepDelta + variance);
    } else {
      dy = direction === ScrollDirection.UP ? -(stepDelta + variance) : stepDelta + variance;
    }

    // Variable delay based on velocity
    const delay = baseDelay / Math.max(0.3, velocity);

    steps.push({ dx, dy, delay: Math.max(1, Math.round(delay)) });
  }

  return steps;
}

/**
 * Execute human-like scroll via CDP
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config - Scroll configuration
 * @returns {Promise<{steps:number, distance:number, duration:number}>}
 */
async function humanScroll(cdp, config) {
  const {
    direction = ScrollDirection.DOWN,
    distance = null, // Auto-calculate if null
    selector = null, // Scroll container (null = window)
    persona = {},
    viewportSize = { width: 1920, height: 1080 }
  } = config;

  // Auto-calculate distance if not provided
  let scrollDistance = distance;
  if (!scrollDistance) {
    scrollDistance = sampleScrollDistance(
      persona.scroll?.meanDistance || 300,
      persona.scroll?.distanceVariance || 0.5
    );
  }

  // Get scroll container if selector provided
  let container = { x: 0, y: 0, width: viewportSize.width, height: viewportSize.height };
  if (selector) {
    try {
      const result = await cdp.send('Runtime.evaluate', {
        expression: `
          (function() {
            const el = document.querySelector(${JSON.stringify(String(selector))});
            if (!el) return null;
            const rect = el.getBoundingClientRect();
            return { x: rect.left, y: rect.top, width: rect.width, height: rect.height, scrollTop: el.scrollTop, scrollLeft: el.scrollLeft, scrollHeight: el.scrollHeight, scrollWidth: el.scrollWidth };
          })()
        `,
        returnByValue: true
      });
      if (result.result?.value) {
        container = result.result.value;
      }
    } catch (e) {
      console.warn('[ScrollMarkov] Failed to get container, using viewport');
    }
  }

  // Generate scroll steps
  const steps = generateScrollSteps({ direction, distance: scrollDistance, viewportSize, persona });

  // Execute scroll via CDP Input.dispatchMouseEvent (wheel)
  let totalDistance = 0;
  for (const step of steps) {
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseWheel',
      x: container.x + container.width / 2,
      y: container.y + container.height / 2,
      deltaX: Math.round(step.dx),
      deltaY: Math.round(step.dy),
      modifiers: 0,
      pointerType: 'mouse'
    });

    totalDistance += Math.sqrt(step.dx * step.dx + step.dy * step.dy);
    await sleep(step.delay);
  }

  // Post-scroll micro-fidget (chance to adjust slightly)
  if (trackedRandom() < (persona.scroll?.fidgetChance || 0.1)) {
    const fidgetSteps = getRandomInt(1, 3);
    for (let i = 0; i < fidgetSteps; i++) {
      const fdx = gaussianRandom(0, 5);
      const fdy = gaussianRandom(0, 5);
      await cdp.send('Input.dispatchMouseEvent', {
        type: 'mouseWheel',
        x: container.x + container.width / 2,
        y: container.y + container.height / 2,
        deltaX: Math.round(fdx),
        deltaY: Math.round(fdy),
        modifiers: 0,
        pointerType: 'mouse'
      });
      await sleep(getRandomInt(50, 150));
    }
  }

  return { steps: steps.length, distance: totalDistance, duration: steps.reduce((a, s) => a + s.delay, 0) };
}

/**
 * Dwell/pause with Weibull distribution (reading time)
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config - Dwell configuration
 */
async function humanDwell(cdp, config) {
  const {
    persona = {},
    minDwell = 500,
    maxDwell = 10000
  } = config;

  // Sample from Weibull (shape < 1 = long reads more likely)
  const shape = persona.scroll?.weibullShape || 0.8;
  const scale = persona.scroll?.weibullScale || 3000;

  let dwellTime = sampleWeibullDwell(shape, scale);
  dwellTime = clamp(dwellTime, minDwell, maxDwell);

  // During dwell, maybe micro-fidget
  const fidgetChance = persona.idle?.fidgetChance || 0.1;
  const fidgetInterval = 1000;

  const startTime = Date.now();
  while (Date.now() - startTime < dwellTime) {
    const remaining = dwellTime - (Date.now() - startTime);
    const interval = Math.min(fidgetInterval, remaining);

    await sleep(interval);

    if (trackedRandom() < fidgetChance) {
      // Small mouse movement during dwell
      await cdp.send('Input.dispatchMouseEvent', {
        type: 'mouseMoved',
        x: Math.round(gaussianRandom(960, 100)),
        y: Math.round(gaussianRandom(540, 100)),
        modifiers: 0,
        button: 'none',
        clickCount: 0
      });
    }
  }

  return { dwellTime };
}

/**
 * CTMC state transition for scroll behavior planning
 * @param {string} currentState - Current scroll state
 * @param {Object} transitions - Transition matrix
 * @returns {string} Next state
 */
function nextScrollState(currentState, transitions = DEFAULT_TRANSITIONS) {
  const probs = transitions[currentState] || transitions[ScrollState.SCROLLING];
  const rand = trackedRandom();
  let cumulative = 0;

  for (const [state, prob] of Object.entries(probs)) {
    cumulative += prob;
    if (rand <= cumulative) return state;
  }

  return ScrollState.SCROLLING; // Fallback
}

/**
 * Plan a scroll session using CTMC
 * @param {Object} config - Session config
 * @returns {Array<{state:string, action:string, params:Object}>}
 */
function planScrollSession(config) {
  const {
    pageCount = 1,
    persona = {},
    maxStates = 20
  } = config;

  const plan = [];
  let currentState = ScrollState.SCANNING; // Start scanning

  for (let i = 0; i < maxStates; i++) {
    const action = selectActionForState(currentState, persona);
    const params = generateActionParams(action, persona);

    plan.push({ state: currentState, action, params });

    // Transition to next state
    currentState = nextScrollState(currentState, persona.scroll?.transitions);

    // Terminal condition
    if (currentState === ScrollState.READING && trackedRandom() < 0.1) {
      break;
    }
  }

  return plan;
}

function selectActionForState(state, persona) {
  const weights = {
    [ScrollState.READING]: { dwell: 0.7, scroll: 0.2, fidget: 0.1 },
    [ScrollState.SCANNING]: { scroll: 0.6, dwell: 0.2, fidget: 0.1, click: 0.1 },
    [ScrollState.SCROLLING]: { scroll: 0.7, dwell: 0.2, fidget: 0.1 },
    [ScrollState.PAUSED]: { dwell: 0.6, scroll: 0.3, fidget: 0.1 },
    [ScrollState.FIDGET]: { fidget: 0.5, scroll: 0.3, dwell: 0.2 }
  };

  const stateWeights = weights[state] || weights[ScrollState.SCROLLING];
  const rand = trackedRandom();
  let cum = 0;

  for (const [action, weight] of Object.entries(stateWeights)) {
    cum += weight;
    if (rand <= cum) return action;
  }

  return 'scroll';
}

function generateActionParams(action, persona) {
  switch (action) {
    case 'scroll':
      return {
        direction: ScrollDirection.DOWN,
        distance: sampleScrollDistance(persona.scroll?.meanDistance, persona.scroll?.distanceVariance)
      };
    case 'dwell':
      return { minDwell: 500, maxDwell: 10000 };
    case 'fidget':
      return { intensity: 'low' };
    case 'click':
      return { chance: persona.scroll?.clickChance || 0.05 };
    default:
      return {};
  }
}

module.exports = {
  ScrollDirection,
  ScrollState,
  DEFAULT_TRANSITIONS,
  sampleWeibullDwell,
  sampleScrollDistance,
  scrollVelocityProfile,
  generateScrollSteps,
  humanScroll,
  humanDwell,
  nextScrollState,
  planScrollSession,
  selectActionForState
};