/**
 * session-engine.js - Master orchestrator for human-like session behavior
 * Ported from QTEProject HumanLike_SessionEngine.js (no spoofing)
 */

'use strict';

const { humanMove, humanClick, humanHover } = require('./mouse-physics');
const { humanScroll, humanDwell } = require('./scroll-markov');
const { idleFidget, preClickSequence, postClickBehavior, readingBehavior, pageOrientation } = require('./micro-habits');
const { generateDwellSchedule } = require('./dwell-weibull');
const { trackedRandom, getRandomInt, sleep } = require('./math-utils');

/**
 * Session phases (NNg 3-phase model)
 */
const SessionPhase = {
  CRITICAL: 'critical',    // 0-10s: orient, overlay, ad impression
  DECISION: 'decision',    // 10-30s: scan, scroll, hover, fidget
  COMMITTED: 'committed',  // 30s+: deep read, select, tab switch
  TRANSITION: 'transition' // Click / exit
};

/**
 * Click lottery bands
 */
const ClickBand = {
  INTERNAL: 'internal',
  EXTERNAL: 'external',
  AD: 'ad'
};

/**
 * Execute a full pageview with human-like behavior
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config - Pageview config
 * @returns {Promise<Object>} Pageview result
 */
async function executePageview(cdp, config) {
  const {
    url,
    persona = {},
    phaseDurations = { critical: 10000, decision: 20000, committed: 30000 },
    clickConfig = { internal: 0.5, external: 0.3, ad: 0.1 },
    viewportSize = { width: 1920, height: 1080 }
  } = config;

  const result = {
    url,
    startTime: Date.now(),
    phases: {},
    actions: [],
    clicks: [],
    scrolls: [],
    dwells: [],
    endReason: 'completed'
  };

  try {
    // === PHASE 1: CRITICAL (0-10s) ===
    console.log('[SessionEngine] Phase: CRITICAL - Page orientation');
    result.phases.critical = await executeCriticalPhase(cdp, { viewportSize, persona });

    // === PHASE 2: DECISION (10-30s) ===
    console.log('[SessionEngine] Phase: DECISION - Scanning & interaction');
    result.phases.decision = await executeDecisionPhase(cdp, {
      phaseDurations,
      clickConfig,
      viewportSize,
      persona,
      actions: result.actions,
      clicks: result.clicks,
      scrolls: result.scrolls,
      dwells: result.dwells
    });

    // === PHASE 3: COMMITTED (30s+) ===
    console.log('[SessionEngine] Phase: COMMITTED - Deep engagement');
    result.phases.committed = await executeCommittedPhase(cdp, {
      phaseDurations,
      clickConfig,
      viewportSize,
      persona,
      actions: result.actions,
      clicks: result.clicks,
      scrolls: result.scrolls,
      dwells: result.dwells
    });

    result.endReason = 'completed';
  } catch (e) {
    console.error('[SessionEngine] Pageview error:', e.message);
    result.endReason = 'error';
    result.error = e.message;
  }

  result.endTime = Date.now();
  result.duration = result.endTime - result.startTime;

  return result;
}

/**
 * Critical phase: Page orientation, overlay dismissal, initial scan
 */
async function executeCriticalPhase(cdp, config) {
  const { viewportSize, persona } = config;
  const phaseResult = { actions: [], duration: 0 };
  const startTime = Date.now();

  // 1. Page orientation (scan down, back up)
  await pageOrientation(cdp, { viewportSize, persona });
  phaseResult.actions.push({ type: 'pageOrientation', timestamp: Date.now() });

  // 2. Initial dwell (page load processing)
  const initialDwell = Math.min(3000, generateDwellSchedule({ preset: 'fast', phases: ['scan'] })[0].duration);
  await sleep(initialDwell);
  phaseResult.actions.push({ type: 'initialDwell', duration: initialDwell, timestamp: Date.now() });

  // 3. Overlay/cookie banner check (would need element detection)
  // Placeholder for future implementation

  phaseResult.duration = Date.now() - startTime;
  return phaseResult;
}

/**
 * Decision phase: Scan, scroll, hover, fidget, click lottery
 */
async function executeDecisionPhase(cdp, config) {
  const { phaseDurations, clickConfig, viewportSize, persona, actions, clicks, scrolls, dwells } = config;
  const phaseResult = { actions: [], clicks: [], scrolls: [], dwells: [] };
  const startTime = Date.now();
  const endTime = startTime + phaseDurations.decision;

  let externalLock = false; // External click lock (QTE pattern)

  while (Date.now() < endTime && !externalLock) {
    // Determine action via click lottery
    const roll = trackedRandom();
    let action = 'scroll';

    if (roll < clickConfig.internal) {
      action = 'clickInternal';
    } else if (roll < clickConfig.internal + clickConfig.external) {
      action = 'clickExternal';
      externalLock = true; // Lock after external click
    } else if (roll < clickConfig.internal + clickConfig.external + clickConfig.ad) {
      action = 'clickAd';
    } else {
      action = 'scroll';
    }

    // Execute action
    switch (action) {
      case 'scroll':
        await executeScrollAction(cdp, { viewportSize, persona, scrolls: phaseResult.scrolls });
        break;
      case 'clickInternal':
        externalLock = await executeClickAction(cdp, { type: 'internal', viewportSize, persona, clicks: phaseResult.clicks });
        break;
      case 'clickExternal':
        externalLock = await executeClickAction(cdp, { type: 'external', viewportSize, persona, clicks: phaseResult.clicks });
        break;
      case 'clickAd':
        await executeClickAction(cdp, { type: 'ad', viewportSize, persona, clicks: phaseResult.clicks });
        break;
    }

    // Micro-fidget chance
    if (trackedRandom() < (persona.idle?.fidgetChance || 0.1)) {
      await idleFidget(cdp, { viewportSize, persona });
      phaseResult.actions.push({ type: 'fidget', timestamp: Date.now() });
    }

    // Dwell between actions
    const interActionDwell = generateDwellSchedule({ preset: 'normal', phases: ['scan'] })[0].duration;
    await sleep(Math.min(interActionDwell, endTime - Date.now()));
  }

  phaseResult.duration = Date.now() - startTime;
  return phaseResult;
}

/**
 * Committed phase: Deep reading, selection, tab switching
 */
async function executeCommittedPhase(cdp, config) {
  const { phaseDurations, clickConfig, viewportSize, persona, actions, clicks, scrolls, dwells } = config;
  const phaseResult = { actions: [], clicks: [], scrolls: [], dwells: [] };
  const startTime = Date.now();
  const endTime = startTime + phaseDurations.committed;

  // Deep reading behavior
  await readingBehavior(cdp, { persona, duration: phaseDurations.committed, viewportSize });

  phaseResult.duration = Date.now() - startTime;
  return phaseResult;
}

/**
 * Execute scroll action with human-like behavior
 */
async function executeScrollAction(cdp, config) {
  const { viewportSize, persona, scrolls } = config;

  const direction = trackedRandom() < 0.85 ? 'down' : 'up'; // 85% down
  const distance = Math.round(200 + trackedRandom() * 500);

  const result = await humanScroll(cdp, { direction, distance, viewportSize, persona });
  scrolls.push({ ...result, direction, timestamp: Date.now() });

  return result;
}

/**
 * Execute click action (internal/external/ad)
 */
async function executeClickAction(cdp, config) {
  const { type, viewportSize, persona, clicks } = config;

  // Find clickable element (simplified - would use CDP DOM.querySelector in reality)
  // For now, simulate click at random content position
  const target = {
    x: viewportSize.width * (0.2 + trackedRandom() * 0.6),
    y: viewportSize.height * (0.2 + trackedRandom() * 0.6)
  };

  // Pre-click sequence
  await preClickSequence(cdp, target, persona);

  // Click
  await humanClick(cdp, { button: 'left', clickCount: 1 });

  // Post-click
  await postClickBehavior(cdp, persona);

  const clickRecord = { type, target, timestamp: Date.now() };
  clicks.push(clickRecord);

  // External click lock
  return type === 'external';
}

/**
 * Run a full session (multiple pageviews)
 * @param {CDPSession} cdp - CDP session
 * @param {Object} config - Session config
 */
async function runSession(cdp, config) {
  const {
    urls = ['about:blank'],
    persona = {},
    maxPages = 10,
    sessionDuration = 300000 // 5 minutes
  } = config;

  const sessionResult = {
    startTime: Date.now(),
    pageviews: [],
    totalClicks: 0,
    totalScrolls: 0,
    totalDuration: 0,
    endReason: 'completed'
  };

  const sessionEndTime = sessionResult.startTime + sessionDuration;

  for (let i = 0; i < Math.min(urls.length, maxPages); i++) {
    if (Date.now() >= sessionEndTime) {
      sessionResult.endReason = 'timeout';
      break;
    }

    const url = urls[i];
    console.log(`[SessionEngine] Pageview ${i + 1}/${urls.length}: ${url}`);

    // Navigate to URL
    try {
      await cdp.send('Page.navigate', { url });
      await cdp.send('Page.loadEventFired'); // Wait for load
    } catch (e) {
      console.warn('[SessionEngine] Navigation failed:', e.message);
    }

    // Execute pageview
    const pageviewResult = await executePageview(cdp, { url, persona });
    sessionResult.pageviews.push(pageviewResult);
    sessionResult.totalClicks += pageviewResult.clicks.length;
    sessionResult.totalScrolls += pageviewResult.scrolls.length;

    // Inter-page delay
    const interPageDelay = generateDwellSchedule({ preset: 'normal', phases: ['scan'] })[0].duration;
    await sleep(Math.min(interPageDelay, sessionEndTime - Date.now()));
  }

  sessionResult.endTime = Date.now();
  sessionResult.totalDuration = sessionResult.endTime - sessionResult.startTime;

  return sessionResult;
}

/**
 * Create default persona configuration
 */
function createPersona(config = {}) {
  const preset = config.preset || 'normal';

  const presets = {
    careful: {
      mouse: { fittsA: 120, fittsB: 180, jitterStd: 2.0, overshootChance: 0.4, overshootPxMin: 10, overshootPxMax: 30 },
      scroll: { meanDistance: 200, distanceVariance: 0.4, weibullShape: 0.8, weibullScale: 4000, fidgetChance: 0.15 },
      click: { preClickPause: 200, preClickVariance: 0.4 },
      idle: { fidgetChance: 0.15, driftRadius: 40, fidgetWeights: { mouseDrift: 0.6, microScroll: 0.2, windowResize: 0.05, tabHover: 0.15 } }
    },
    normal: {
      mouse: { fittsA: 100, fittsB: 150, jitterStd: 1.5, overshootChance: 0.3, overshootPxMin: 5, overshootPxMax: 20 },
      scroll: { meanDistance: 300, distanceVariance: 0.5, weibullShape: 0.8, weibullScale: 3000, fidgetChance: 0.1 },
      click: { preClickPause: 150, preClickVariance: 0.3 },
      idle: { fidgetChance: 0.1, driftRadius: 30, fidgetWeights: { mouseDrift: 0.5, microScroll: 0.2, windowResize: 0.1, tabHover: 0.2 } }
    },
    fast: {
      mouse: { fittsA: 80, fittsB: 120, jitterStd: 1.0, overshootChance: 0.2, overshootPxMin: 3, overshootPxMax: 15 },
      scroll: { meanDistance: 500, distanceVariance: 0.6, weibullShape: 0.6, weibullScale: 2000, fidgetChance: 0.05 },
      click: { preClickPause: 80, preClickVariance: 0.2 },
      idle: { fidgetChance: 0.05, driftRadius: 20, fidgetWeights: { mouseDrift: 0.4, microScroll: 0.3, windowResize: 0.15, tabHover: 0.15 } }
    },
    elderly: {
      mouse: { fittsA: 150, fittsB: 200, jitterStd: 2.5, overshootChance: 0.5, overshootPxMin: 15, overshootPxMax: 40 },
      scroll: { meanDistance: 150, distanceVariance: 0.3, weibullShape: 0.9, weibullScale: 5000, fidgetChance: 0.2 },
      click: { preClickPause: 300, preClickVariance: 0.5 },
      idle: { fidgetChance: 0.2, driftRadius: 50, fidgetWeights: { mouseDrift: 0.7, microScroll: 0.1, windowResize: 0.05, tabHover: 0.15 } }
    }
  };

  return { ...presets[preset], ...config };
}

module.exports = {
  SessionPhase,
  ClickBand,
  executePageview,
  executeCriticalPhase,
  executeDecisionPhase,
  executeCommittedPhase,
  executeScrollAction,
  executeClickAction,
  runSession,
  createPersona
};