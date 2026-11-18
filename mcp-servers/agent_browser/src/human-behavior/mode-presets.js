/**
 * mode-presets.js - Behavior presets for different user types
 * Ported from QTEProject HumanLike_ModePresets.js
 */

'use strict';

/**
 * Get mode configuration preset
 * @param {string} mode - Mode name
 * @returns {Object} Complete persona configuration
 */
function getModeConfig(mode = 'normal') {
  const presets = {
    // Careful, deliberate user - reads thoroughly, precise movements
    careful: {
      mouse: {
        fittsA: 120,
        fittsB: 180,
        jitterStd: 2.0,
        overshootChance: 0.4,
        overshootPxMin: 10,
        overshootPxMax: 30,
        targetWidth: 15,
        targetHeight: 15,
        directionalBias: 0
      },
      scroll: {
        meanDistance: 200,
        distanceVariance: 0.4,
        weibullShape: 0.8,
        weibullScale: 4000,
        fidgetChance: 0.15,
        clickChance: 0.03,
        reReadChance: 0.15
      },
      click: {
        preClickPause: 200,
        preClickVariance: 0.4,
        postClickPause: 300
      },
      typing: {
        baseSpeedMs: 180,
        burstVariance: 0.4,
        errorRate: 0.03,
        correctionDelay: 200
      },
      idle: {
        fidgetChance: 0.15,
        driftRadius: 40,
        fidgetWeights: { mouseDrift: 0.6, microScroll: 0.2, windowResize: 0.05, tabHover: 0.15 },
        mouseDriftChance: 0.1
      },
      dwell: {
        reading: { shape: 1.0, scale: 8000 },
        scan: { shape: 0.7, scale: 3000 },
        deepRead: { shape: 1.3, scale: 10000 }
      }
    },

    // Normal user - balanced behavior
    normal: {
      mouse: {
        fittsA: 100,
        fittsB: 150,
        jitterStd: 1.5,
        overshootChance: 0.3,
        overshootPxMin: 5,
        overshootPxMax: 20,
        targetWidth: 20,
        targetHeight: 20,
        directionalBias: 0
      },
      scroll: {
        meanDistance: 300,
        distanceVariance: 0.5,
        weibullShape: 0.8,
        weibullScale: 3000,
        fidgetChance: 0.1,
        clickChance: 0.05,
        reReadChance: 0.08
      },
      click: {
        preClickPause: 150,
        preClickVariance: 0.3,
        postClickPause: 200
      },
      typing: {
        baseSpeedMs: 120,
        burstVariance: 0.3,
        errorRate: 0.02,
        correctionDelay: 150
      },
      idle: {
        fidgetChance: 0.1,
        driftRadius: 30,
        fidgetWeights: { mouseDrift: 0.5, microScroll: 0.2, windowResize: 0.1, tabHover: 0.2 },
        mouseDriftChance: 0.05
      },
      dwell: {
        reading: { shape: 0.8, scale: 6000 },
        scan: { shape: 0.6, scale: 2000 },
        deepRead: { shape: 1.2, scale: 8000 }
      }
    },

    // Fast user - quick scans, rapid clicks
    fast: {
      mouse: {
        fittsA: 80,
        fittsB: 120,
        jitterStd: 1.0,
        overshootChance: 0.2,
        overshootPxMin: 3,
        overshootPxMax: 15,
        targetWidth: 25,
        targetHeight: 25,
        directionalBias: 0
      },
      scroll: {
        meanDistance: 500,
        distanceVariance: 0.6,
        weibullShape: 0.6,
        weibullScale: 2000,
        fidgetChance: 0.05,
        clickChance: 0.1,
        reReadChance: 0.03
      },
      click: {
        preClickPause: 80,
        preClickVariance: 0.2,
        postClickPause: 100
      },
      typing: {
        baseSpeedMs: 80,
        burstVariance: 0.25,
        errorRate: 0.015,
        correctionDelay: 100
      },
      idle: {
        fidgetChance: 0.05,
        driftRadius: 20,
        fidgetWeights: { mouseDrift: 0.4, microScroll: 0.3, windowResize: 0.15, tabHover: 0.15 },
        mouseDriftChance: 0.03
      },
      dwell: {
        reading: { shape: 0.7, scale: 4000 },
        scan: { shape: 0.5, scale: 1500 },
        deepRead: { shape: 1.0, scale: 5000 }
      }
    },

    // Elderly user - slower, more deliberate, larger targets
    elderly: {
      mouse: {
        fittsA: 150,
        fittsB: 200,
        jitterStd: 2.5,
        overshootChance: 0.5,
        overshootPxMin: 15,
        overshootPxMax: 40,
        targetWidth: 30,
        targetHeight: 30,
        directionalBias: 0
      },
      scroll: {
        meanDistance: 150,
        distanceVariance: 0.3,
        weibullShape: 0.9,
        weibullScale: 5000,
        fidgetChance: 0.2,
        clickChance: 0.02,
        reReadChance: 0.2
      },
      click: {
        preClickPause: 300,
        preClickVariance: 0.5,
        postClickPause: 500
      },
      typing: {
        baseSpeedMs: 250,
        burstVariance: 0.5,
        errorRate: 0.04,
        correctionDelay: 400
      },
      idle: {
        fidgetChance: 0.2,
        driftRadius: 50,
        fidgetWeights: { mouseDrift: 0.7, microScroll: 0.1, windowResize: 0.05, tabHover: 0.15 },
        mouseDriftChance: 0.15
      },
      dwell: {
        reading: { shape: 0.9, scale: 10000 },
        scan: { shape: 0.7, scale: 4000 },
        deepRead: { shape: 1.1, scale: 15000 }
      }
    },

    // Power user - keyboard shortcuts, fast navigation, minimal idle
    power_user: {
      mouse: {
        fittsA: 70,
        fittsB: 100,
        jitterStd: 0.8,
        overshootChance: 0.15,
        overshootPxMin: 2,
        overshootPxMax: 10,
        targetWidth: 18,
        targetHeight: 18,
        directionalBias: 0
      },
      scroll: {
        meanDistance: 600,
        distanceVariance: 0.7,
        weibullShape: 0.5,
        weibullScale: 1500,
        fidgetChance: 0.03,
        clickChance: 0.15,
        reReadChance: 0.02
      },
      click: {
        preClickPause: 50,
        preClickVariance: 0.15,
        postClickPause: 50
      },
      typing: {
        baseSpeedMs: 60,
        burstVariance: 0.2,
        errorRate: 0.01,
        correctionDelay: 80
      },
      idle: {
        fidgetChance: 0.02,
        driftRadius: 15,
        fidgetWeights: { mouseDrift: 0.3, microScroll: 0.4, windowResize: 0.2, tabHover: 0.1 },
        mouseDriftChance: 0.01
      },
      dwell: {
        reading: { shape: 0.6, scale: 3000 },
        scan: { shape: 0.4, scale: 1000 },
        deepRead: { shape: 0.9, scale: 4000 }
      }
    },

    // Mobile user - touch-like behavior, larger targets
    mobile: {
      mouse: {
        fittsA: 110,
        fittsB: 160,
        jitterStd: 2.0,
        overshootChance: 0.35,
        overshootPxMin: 8,
        overshootPxMax: 25,
        targetWidth: 44, // Touch target size
        targetHeight: 44,
        directionalBias: 0
      },
      scroll: {
        meanDistance: 400,
        distanceVariance: 0.5,
        weibullShape: 0.7,
        weibullScale: 2500,
        fidgetChance: 0.12,
        clickChance: 0.06,
        reReadChance: 0.1
      },
      click: {
        preClickPause: 180,
        preClickVariance: 0.35,
        postClickPause: 250
      },
      typing: {
        baseSpeedMs: 200,
        burstVariance: 0.4,
        errorRate: 0.035,
        correctionDelay: 250
      },
      idle: {
        fidgetChance: 0.08,
        driftRadius: 35,
        fidgetWeights: { mouseDrift: 0.4, microScroll: 0.3, windowResize: 0.15, tabHover: 0.15 },
        mouseDriftChance: 0.08
      },
      dwell: {
        reading: { shape: 0.75, scale: 5000 },
        scan: { shape: 0.55, scale: 1800 },
        deepRead: { shape: 1.1, scale: 7000 }
      }
    }
  };

  const config = presets[mode] || presets.normal;

  // Add metadata
  config._meta = {
    mode,
    description: getModeDescription(mode),
    createdAt: new Date().toISOString()
  };

  return config;
}

function getModeDescription(mode) {
  const descriptions = {
    careful: 'Careful, deliberate user who reads thoroughly and moves precisely',
    normal: 'Balanced average user behavior',
    fast: 'Quick scanning user with rapid interactions',
    elderly: 'Slower, more deliberate user with larger target preferences',
    power_user: 'Expert user with keyboard shortcuts and minimal idle time',
    mobile: 'Touch-like behavior with larger targets and gesture patterns'
  };
  return descriptions[mode] || descriptions.normal;
}

/**
 * List all available modes
 */
function listModes() {
  return [
    { id: 'careful', name: 'Careful', description: getModeDescription('careful') },
    { id: 'normal', name: 'Normal', description: getModeDescription('normal') },
    { id: 'fast', name: 'Fast', description: getModeDescription('fast') },
    { id: 'elderly', name: 'Elderly', description: getModeDescription('elderly') },
    { id: 'power_user', name: 'Power User', description: getModeDescription('power_user') },
    { id: 'mobile', name: 'Mobile', description: getModeDescription('mobile') }
  ];
}

/**
 * Merge custom config with preset
 */
function mergeWithPreset(mode, customConfig = {}) {
  const preset = getModeConfig(mode);
  return deepMerge(preset, customConfig);
}

function deepMerge(target, source) {
  const result = { ...target };
  for (const key of Object.keys(source)) {
    if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
      result[key] = deepMerge(target[key] || {}, source[key]);
    } else {
      result[key] = source[key];
    }
  }
  return result;
}

module.exports = {
  getModeConfig,
  listModes,
  mergeWithPreset,
  getModeDescription
};