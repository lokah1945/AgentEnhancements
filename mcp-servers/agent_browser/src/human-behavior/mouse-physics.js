/**
 * mouse-physics.js - Human-like mouse movement using Fitts's Law + Bezier curves
 * Ported from QTEProject HumanLike_MousePhysics.js (no spoofing)
 */

'use strict';

const {
  gaussianRandom,
  clamp,
  cubicBezierPoint,
  fittsMovementTime,
  easeInOutSine,
  getRandomInt,
  sleep,
  trackedRandom,
  distance,
  angle,
  perpendicularOffset
} = require('./math-utils');

/**
 * Get initial mouse position for a session
 * @param {{width:number,height:number}} viewportSize
 * @returns {{x:number,y:number}}
 */
function getInitialMousePos(viewportSize) {
  return {
    x: Math.round(viewportSize.width * 0.4),
    y: Math.round(viewportSize.height * 0.3)
  };
}

/**
 * Calculate target point within element box (70% inner zone preference)
 * @param {{x:number,y:number,width:number,height:number}} box
 * @returns {{x:number,y:number}}
 */
function calculateTargetPoint(box) {
  const useInner = trackedRandom() < 0.70;

  if (useInner) {
    const mx = box.width * 0.15;
    const my = box.height * 0.15;
    return {
      x: box.x + mx + trackedRandom() * (box.width - 2 * mx),
      y: box.y + my + trackedRandom() * (box.height - 2 * my)
    };
  } else {
    return {
      x: box.x + trackedRandom() * box.width,
      y: box.y + trackedRandom() * box.height
    };
  }
}

/**
 * Generate Bezier control points for natural mouse path
 * @param {{x:number,y:number}} start
 * @param {{x:number,y:number}} end
 * @param {Object} persona - Persona config for directional bias
 * @returns {{p1:{x:number,y:number}, p2:{x:number,y:number}}}
 */
function generateControlPoints(start, end, persona = {}) {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dist = Math.sqrt(dx * dx + dy * dy);

  if (dist === 0) {
    return { p1: { ...start }, p2: { ...end } };
  }

  const perpX = -dy / dist;
  const perpY = dx / dist;

  // Persona-based directional bias
  const bias = persona.mouse?.directionalBias || 0;
  const biasX = Math.cos(bias) * dist * 0.1;
  const biasY = Math.sin(bias) * dist * 0.1;

  // Control point 1: ~30% along, perpendicular offset
  const cp1Dist = dist * (0.1 + trackedRandom() * 0.3); // 10-40% of distance
  const cp1Side = trackedRandom() < 0.5 ? -1 : 1;
  const p1 = {
    x: start.x + dx * 0.3 + perpX * cp1Dist * cp1Side + biasX,
    y: start.y + dy * 0.3 + perpY * cp1Dist * cp1Side + biasY
  };

  // Control point 2: ~70% along, smaller perpendicular offset
  const cp2Dist = dist * (0.05 + trackedRandom() * 0.15); // 5-20% of distance
  const cp2Side = trackedRandom() < 0.5 ? -1 : 1;
  const p2 = {
    x: start.x + dx * 0.7 + perpX * cp2Dist * cp2Side - biasX,
    y: start.y + dy * 0.7 + perpY * cp2Dist * cp2Side - biasY
  };

  return { p1, p2 };
}

/**
 * Human-like mouse move using CDP Input.dispatchMouseEvent
 * @param {CDPSession} cdp - CDP session
 * @param {{x:number,y:number}} target - Target position
 * @param {Object} options - Movement options
 * @param {{x:number,y:number}} options.currentPos - Current mouse position (required for per-session tracking)
 * @returns {Promise<{steps:number, duration:number, finalPos:{x:number,y:number}}>}
 */
async function humanMove(cdp, target, options = {}) {
  const {
    persona = {},
    viewportSize = { width: 1920, height: 1080 },
    currentPos,
    onStep = null
  } = options;

  // Use provided currentPos or initialize
  const start = currentPos ? { ...currentPos } : getInitialMousePos(viewportSize);
  const end = { ...target };

  // Calculate movement parameters
  const dist = distance(start, end);
  const targetWidth = Math.min(
    persona.mouse?.targetWidth || 20,
    Math.max(persona.mouse?.targetHeight || 20, 10)
  );

  // Fitts's Law with Gaussian variance (±46.4%)
  const mtBase = fittsMovementTime(dist, targetWidth,
    persona.mouse?.fittsA || 100,
    persona.mouse?.fittsB || 150
  );
  const mtActual = mtBase * Math.max(0.1, 1 + gaussianRandom(0, 0.464));

  // Generate Bezier path
  const { p1, p2 } = generateControlPoints(start, end, persona);

  // Calculate steps (minimum 10, maximum based on distance)
  const stepCount = clamp(Math.round(dist / 3), 10, 100);
  const baseStepTime = mtActual / stepCount;

  // Jitter standard deviation from persona
  const jitterStd = persona.mouse?.jitterStd || 1.5;

  // Overshoot parameters
  const overshootChance = persona.mouse?.overshootChance || 0.3;
  const overshootMin = persona.mouse?.overshootPxMin || 5;
  const overshootMax = persona.mouse?.overshootPxMax || 20;
  const doOvershoot = trackedRandom() < overshootChance && dist > 50;

  let overshootTarget = null;
  let correctionSteps = [];

  if (doOvershoot) {
    const overshootDist = overshootMin + trackedRandom() * (overshootMax - overshootMin);
    const moveAngle = angle(start, end);
    const overshootAngle = moveAngle + gaussianRandom(0, 15 * Math.PI / 180); // ±15 degrees
    overshootTarget = {
      x: end.x + Math.cos(overshootAngle) * overshootDist,
      y: end.y + Math.sin(overshootAngle) * overshootDist
    };

    // Correction: 1-3 saccades back to target
    const correctionCount = 1 + getRandomInt(0, 2);
    for (let i = 0; i < correctionCount; i++) {
      const ratio = (i + 1) / (correctionCount + 1);
      correctionSteps.push({
        x: overshootTarget.x + (end.x - overshootTarget.x) * ratio + gaussianRandom(0, 2),
        y: overshootTarget.y + (end.y - overshootTarget.y) * ratio + gaussianRandom(0, 2)
      });
    }
  }

  // Execute movement phases
  const phases = [
    { name: 'approach', points: [end] },
    ...(doOvershoot ? [
      { name: 'overshoot', points: [overshootTarget] },
      ...correctionSteps.map((pt, i) => ({ name: `correction${i + 1}`, points: [pt] }))
    ] : [])
  ];

  let totalSteps = 0;
  let currentMousePos = { ...start };

  for (const phase of phases) {
    const phaseStart = { ...currentMousePos };
    const phaseEnd = phase.points[0];
    const phaseDist = distance(phaseStart, phaseEnd);

    if (phaseDist < 1) continue;

    const phaseSteps = clamp(Math.round(phaseDist / 2), 5, 30);
    const { p1: p1p, p2: p2p } = generateControlPoints(phaseStart, phaseEnd, persona);

    for (let i = 1; i <= phaseSteps; i++) {
      const t = i / phaseSteps;
      const easedT = easeInOutSine(t);
      const point = cubicBezierPoint(easedT, phaseStart, p1p, p2p, phaseEnd);

      // Add hand tremor (Gaussian jitter per step)
      const jitterX = gaussianRandom(0, jitterStd);
      const jitterY = gaussianRandom(0, jitterStd);

      const finalX = clamp(Math.round(point.x + jitterX), 0, viewportSize.width);
      const finalY = clamp(Math.round(point.y + jitterY), 0, viewportSize.height);

      // Send mousemove via CDP
      await cdp.send('Input.dispatchMouseEvent', {
        type: 'mouseMoved',
        x: finalX,
        y: finalY,
        modifiers: 0,
        button: 'none',
        clickCount: 0
      });

      currentMousePos = { x: finalX, y: finalY };

      if (onStep) {
        onStep({ x: finalX, y: finalY, phase: phase.name, step: i, total: phaseSteps });
      }

      // Velocity-adaptive timing
      const velocity = easeInOutSine(t);
      const stepDelay = baseStepTime / Math.max(0.2, velocity);
      await sleep(Math.max(1, Math.round(stepDelay)));

      totalSteps++;
    }
  }

  return { steps: totalSteps, duration: mtActual, overshoot: doOvershoot, finalPos: currentMousePos };
}

/**
 * Click at current position with human-like timing
 * @param {CDPSession} cdp - CDP session
 * @param {Object} options - Click options
 * @param {{x:number,y:number}} options.currentPos - Current mouse position
 * @returns {Promise<{finalPos:{x:number,y:number}}>}
 */
async function humanClick(cdp, options = {}) {
  const {
    button = 'left',
    clickCount = 1,
    modifiers = [],
    delay = 50,
    currentPos = { x: 960, y: 540 }
  } = options;

  const modMap = { 'Alt': 1, 'Control': 2, 'Meta': 4, 'Shift': 8 };
  const modValue = modifiers.reduce((acc, m) => acc + (modMap[m] || 0), 0);
  const buttonMap = { 'left': 'left', 'right': 'right', 'middle': 'middle' };

  let currentMousePos = { ...currentPos };

  for (let i = 0; i < clickCount; i++) {
    // Mouse down
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mousePressed',
      x: currentMousePos.x,
      y: currentMousePos.y,
      modifiers: modValue,
      button: buttonMap[button] || 'left',
      clickCount: i + 1
    });

    await sleep(delay + getRandomInt(-10, 10));

    // Mouse up
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased',
      x: currentMousePos.x,
      y: currentMousePos.y,
      modifiers: modValue,
      button: buttonMap[button] || 'left',
      clickCount: i + 1
    });

    if (i < clickCount - 1) {
      await sleep(getRandomInt(80, 150)); // Between clicks
    }
  }

  return { finalPos: currentMousePos };
}

/**
 * Hover element with approach and settle
 * @param {CDPSession} cdp - CDP session
 * @param {{x:number,y:number}} target - Target position
 * @param {Object} options - Hover options
 * @returns {Promise<{finalPos:{x:number,y:number}}>}
 */
async function humanHover(cdp, target, options = {}) {
  const { duration = 1000, persona = {}, currentPos } = options;

  const moveResult = await humanMove(cdp, target, { persona, currentPos });

  // Settle - small micro-movements
  const settleSteps = 3;
  let currentMousePos = moveResult.finalPos;
  for (let i = 0; i < settleSteps; i++) {
    const jitterX = gaussianRandom(0, 0.5);
    const jitterY = gaussianRandom(0, 0.5);
    currentMousePos = {
      x: clamp(Math.round(currentMousePos.x + jitterX), 0, 1920),
      y: clamp(Math.round(currentMousePos.y + jitterY), 0, 1080)
    };
    await cdp.send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      x: currentMousePos.x,
      y: currentMousePos.y,
      modifiers: 0,
      button: 'none',
      clickCount: 0
    });
    await sleep(duration / settleSteps);
  }

  return { finalPos: currentMousePos };
}

/**
 * Drag and drop with Bezier path
 * @param {CDPSession} cdp - CDP session
 * @param {{x:number,y:number}} source
 * @param {{x:number,y:number}} target
 * @param {Object} options
 * @returns {Promise<{finalPos:{x:number,y:number}}>}
 */
async function humanDragDrop(cdp, source, target, options = {}) {
  const { persona = {}, currentPos } = options;

  // Move to source
  const moveToSource = await humanMove(cdp, source, { persona, currentPos });

  // Mouse down
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: moveToSource.finalPos.x,
    y: moveToSource.finalPos.y,
    modifiers: 0,
    button: 'left',
    clickCount: 1
  });

  await sleep(getRandomInt(100, 200));

  // Drag to target
  const moveToTarget = await humanMove(cdp, target, { persona, currentPos: moveToSource.finalPos });

  await sleep(getRandomInt(50, 150));

  // Mouse up
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: moveToTarget.finalPos.x,
    y: moveToTarget.finalPos.y,
    modifiers: 0,
    button: 'left',
    clickCount: 1
  });

  return { finalPos: moveToTarget.finalPos };
}

module.exports = {
  getInitialMousePos,
  calculateTargetPoint,
  generateControlPoints,
  humanMove,
  humanClick,
  humanHover,
  humanDragDrop
};