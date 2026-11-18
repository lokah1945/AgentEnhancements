/**
 * dwell-weibull.js - Weibull-distributed dwell times for human reading patterns
 * Ported from QTEProject HumanLike_DwellWeibull.js (no spoofing)
 */

'use strict';

/**
 * Weibull distribution sampling
 * Used for modeling human reading/dwell times
 * Shape < 1: decreasing hazard rate (longer reads become more likely)
 * Shape > 1: increasing hazard rate (shorter reads more likely)
 * Shape = 1: exponential distribution
 *
 * @param {number} shape - Shape parameter (k)
 * @param {number} scale - Scale parameter (λ) in milliseconds
 * @returns {number} Sampled dwell time in milliseconds
 */
function sampleWeibull(shape = 0.8, scale = 3000) {
  if (shape <= 0 || scale <= 0) {
    throw new Error('Weibull parameters must be positive');
  }

  // Inverse transform sampling: λ * (-ln(1-U))^(1/k)
  const u = Math.random();
  return scale * Math.pow(-Math.log(1 - u), 1 / shape);
}

/**
 * Generate dwell time for reading content
 * Based on content length and reading speed
 *
 * @param {Object} config
 * @param {number} config.wordCount - Number of words to read
 * @param {number} config.wpm - Words per minute (default 200)
 * @param {number} config.shape - Weibull shape (default 0.8)
 * @param {number} config.scaleBase - Base scale factor (default 60000ms = 1min)
 * @param {number} config.minDwell - Minimum dwell (ms)
 * @param {number} config.maxDwell - Maximum dwell (ms)
 * @returns {number} Dwell time in milliseconds
 */
function generateReadingDwell(config = {}) {
  const {
    wordCount = 200,
    wpm = 200,
    shape = 0.8,
    scaleBase = 60000,
    minDwell = 500,
    maxDwell = 120000
  } = config;

  // Base time from reading speed
  const baseTimeMs = (wordCount / wpm) * 60000;

  // Scale based on content length
  const scale = scaleBase * (baseTimeMs / 30000); // Normalize to 30s base

  // Sample from Weibull
  let dwell = sampleWeibull(shape, scale);

  // Clamp to bounds
  return clamp(dwell, minDwell, maxDwell);
}

/**
 * Generate scan dwell (quick look, not deep reading)
 * Shorter, more variable
 */
function generateScanDwell(config = {}) {
  const {
    shape = 0.6,    // More variable
    scale = 2000,   // Shorter
    minDwell = 200,
    maxDwell = 5000
  } = config;

  let dwell = sampleWeibull(shape, scale);
  return clamp(dwell, minDwell, maxDwell);
}

/**
 * Generate deep reading dwell (focused reading)
 * Longer, less variable
 */
function generateDeepReadDwell(config = {}) {
  const {
    shape = 1.2,      // More consistent
    scale = 8000,     // Longer
    minDwell = 2000,
    maxDwell = 180000
  } = config;

  let dwell = sampleWeibull(shape, scale);
  return clamp(dwell, minDwell, maxDwell);
}

/**
 * Generate re-read dwell (going back to re-read)
 * Short, decisive
 */
function generateReReadDwell(config = {}) {
  const {
    shape = 1.5,
    scale = 1500,
    minDwell = 500,
    maxDwell = 8000
  } = config;

  let dwell = sampleWeibull(shape, scale);
  return clamp(dwell, minDwell, maxDwell);
}

/**
 * Clamp value
 */
function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

/**
 * Persona-based dwell configuration presets
 */
const DWELL_PRESETS = {
  careful: {
    reading: { shape: 1.0, scale: 8000, minDwell: 1000, maxDwell: 120000 },
    scan: { shape: 0.7, scale: 3000, minDwell: 300, maxDwell: 8000 },
    deepRead: { shape: 1.3, scale: 10000, minDwell: 3000, maxDwell: 240000 },
    reRead: { shape: 1.5, scale: 2000, minDwell: 800, maxDwell: 15000 }
  },
  normal: {
    reading: { shape: 0.8, scale: 6000, minDwell: 500, maxDwell: 120000 },
    scan: { shape: 0.6, scale: 2000, minDwell: 200, maxDwell: 5000 },
    deepRead: { shape: 1.2, scale: 8000, minDwell: 2000, maxDwell: 180000 },
    reRead: { shape: 1.5, scale: 1500, minDwell: 500, maxDwell: 8000 }
  },
  fast: {
    reading: { shape: 0.7, scale: 4000, minDwell: 300, maxDwell: 60000 },
    scan: { shape: 0.5, scale: 1500, minDwell: 100, maxDwell: 3000 },
    deepRead: { shape: 1.0, scale: 5000, minDwell: 1000, maxDwell: 90000 },
    reRead: { shape: 1.3, scale: 1000, minDwell: 300, maxDwell: 5000 }
  },
  elderly: {
    reading: { shape: 0.9, scale: 10000, minDwell: 2000, maxDwell: 240000 },
    scan: { shape: 0.7, scale: 4000, minDwell: 500, maxDwell: 15000 },
    deepRead: { shape: 1.1, scale: 15000, minDwell: 5000, maxDwell: 300000 },
    reRead: { shape: 1.3, scale: 3000, minDwell: 1500, maxDwell: 30000 }
  }
};

/**
 * Get dwell preset for persona
 * @param {string} presetName - Preset name
 * @param {string} type - Dwell type (reading, scan, deepRead, reRead)
 * @returns {Object} Preset config
 */
function getDwellPreset(presetName = 'normal', type = 'reading') {
  const preset = DWELL_PRESETS[presetName] || DWELL_PRESETS.normal;
  return preset[type] || preset.reading;
}

/**
 * Sample dwell from preset
 * @param {string} presetName
 * @param {string} type
 * @returns {number} Dwell time in ms
 */
function sampleDwell(presetName = 'normal', type = 'reading') {
  const config = getDwellPreset(presetName, type);
  return sampleWeibull(config.shape, config.scale);
}

/**
 * Generate session dwell schedule (for a full page visit)
 * @param {Object} config
 * @returns {Array<{type:string, duration:number, cumulative:number}>}
 */
function generateDwellSchedule(config = {}) {
  const {
    preset = 'normal',
    phases = ['scan', 'read', 'scan', 'deepRead', 'scan'],
    persona = {}
  } = config;

  const schedule = [];
  let cumulative = 0;

  for (const phase of phases) {
    const dwell = sampleDwell(preset, phase);
    cumulative += dwell;
    schedule.push({ type: phase, duration: dwell, cumulative });
  }

  return schedule;
}

module.exports = {
  sampleWeibull,
  generateReadingDwell,
  generateScanDwell,
  generateDeepReadDwell,
  generateReReadDwell,
  DWELL_PRESETS,
  getDwellPreset,
  sampleDwell,
  generateDwellSchedule
};