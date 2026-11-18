/**
 * math-utils.js - Mathematical utilities for human behavior
 * Ported from QTEProject HumanLike_Math.js (no spoofing, pure math)
 */

'use strict';

/**
 * Gaussian random number generator (Box-Muller transform)
 * @param {number} mean - Mean (default 0)
 * @param {number} stdDev - Standard deviation (default 1)
 * @returns {number} Gaussian random number
 */
function gaussianRandom(mean = 0, stdDev = 1) {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
  return z * stdDev + mean;
}

/**
 * Clamp value between min and max
 * @param {number} value
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

/**
 * Cubic Bezier point calculation
 * @param {number} t - Parameter (0-1)
 * @param {{x:number,y:number}} p0 - Start point
 * @param {{x:number,y:number}} p1 - Control point 1
 * @param {{x:number,y:number}} p2 - Control point 2
 * @param {{x:number,y:number}} p3 - End point
 * @returns {{x:number,y:number}} Point on curve
 */
function cubicBezierPoint(t, p0, p1, p2, p3) {
  const u = 1 - t;
  const uu = u * u;
  const uuu = uu * u;
  const tt = t * t;
  const ttt = tt * t;

  return {
    x: uuu * p0.x + 3 * uu * t * p1.x + 3 * u * tt * p2.x + ttt * p3.x,
    y: uuu * p0.y + 3 * uu * t * p1.y + 3 * u * tt * p2.y + ttt * p3.y
  };
}

/**
 * Fitts's Law movement time calculation
 * MT = a + b * log2(D/W + 1)
 * @param {number} distance - Euclidean distance to target
 * @param {number} targetWidth - Effective target width (min of width/height)
 * @param {number} a - Intercept (default 100ms)
 * @param {number} b - Slope (default 150ms)
 * @returns {number} Movement time in ms
 */
function fittsMovementTime(distance, targetWidth, a = 100, b = 150) {
  if (targetWidth <= 0) targetWidth = 1;
  const indexOfDifficulty = Math.log2(distance / targetWidth + 1);
  return a + b * indexOfDifficulty;
}

/**
 * Sine ease-in-out velocity profile
 * @param {number} t - Progress (0-1)
 * @returns {number} Velocity multiplier
 */
function easeInOutSine(t) {
  return Math.sin(Math.PI * t);
}

/**
 * Generate random integer in range [min, max]
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
function getRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Sleep/promise delay
 * @param {number} ms - Milliseconds
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Human-like delay with variance
 * @param {number} baseMs - Base delay
 * @param {number} variance - Variance factor (default 0.3)
 * @returns {number} Actual delay
 */
function getHumanDelay(baseMs, variance = 0.3) {
  const varianceMs = baseMs * variance;
  return baseMs + (Math.random() - 0.5) * 2 * varianceMs;
}

/**
 * Tracked random for entropy tracking
 * @returns {number} Random value 0-1
 */
let _entropyCounter = 0;
let _entropyLog = [];

function trackedRandom() {
  const value = Math.random();
  _entropyCounter++;
  _entropyLog.push({ index: _entropyCounter, value, timestamp: Date.now() });
  if (_entropyLog.length > 10000) _entropyLog.shift();
  return value;
}

function getEntropyStats() {
  return {
    count: _entropyCounter,
    log: _entropyLog.slice(-100)
  };
}

function resetEntropy() {
  _entropyCounter = 0;
  _entropyLog = [];
}

/**
 * Distance between two points
 * @param {{x:number,y:number}} p1
 * @param {{x:number,y:number}} p2
 * @returns {number}
 */
function distance(p1, p2) {
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  return Math.sqrt(dx * dx + dy * dy);
}

/**
 * Angle between two points (radians)
 * @param {{x:number,y:number}} from
 * @param {{x:number,y:number}} to
 * @returns {number}
 */
function angle(from, to) {
  return Math.atan2(to.y - from.y, to.x - from.x);
}

/**
 * Perpendicular point offset
 * @param {{x:number,y:number}} p1
 * @param {{x:number,y:number}} p2
 * @param {number} distance
 * @param {number} side - -1 or 1
 * @returns {{x:number,y:number}}
 */
function perpendicularOffset(p1, p2, distance, side = 1) {
  const ang = angle(p1, p2) + (side * Math.PI / 2);
  return {
    x: p1.x + Math.cos(ang) * distance,
    y: p1.y + Math.sin(ang) * distance
  };
}

module.exports = {
  gaussianRandom,
  clamp,
  cubicBezierPoint,
  fittsMovementTime,
  easeInOutSine,
  getRandomInt,
  sleep,
  getHumanDelay,
  trackedRandom,
  getEntropyStats,
  resetEntropy,
  distance,
  angle,
  perpendicularOffset
};