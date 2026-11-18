/**
 * profiles.js - User persona generation and management
 * Ported from QTEProject HumanLike_Profiles.js (no spoofing)
 */

'use strict';

const { getModeConfig } = require('./mode-presets');
const { trackedRandom } = require('./math-utils');

/**
 * Generate a complete user persona
 * @param {Object} config - Persona configuration
 * @returns {Object} Complete persona object
 */
function generatePersona(config = {}) {
  const mode = config.mode || 'normal';
  const baseConfig = getModeConfig(mode);

  // Override with custom config
  const persona = deepMerge(baseConfig, config);

  // Add unique identifiers
  persona.id = `persona_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  persona.mode = mode;
  persona.createdAt = new Date().toISOString();

  // Add behavioral entropy seed
  persona.entropySeed = generateEntropySeed();

  // Add session-specific variations
  persona.sessionVariation = generateSessionVariation();

  return persona;
}

/**
 * Generate entropy seed for deterministic randomness within session
 */
function generateEntropySeed() {
  return Math.random().toString(36).substr(2, 16);
}

/**
 * Generate session-specific behavioral variations
 */
function generateSessionVariation() {
  return {
    mouseSpeedMultiplier: 0.8 + trackedRandom() * 0.4,      // 0.8 - 1.2
    scrollSpeedMultiplier: 0.7 + trackedRandom() * 0.6,      // 0.7 - 1.3
    clickSpeedMultiplier: 0.8 + trackedRandom() * 0.4,       // 0.8 - 1.2
    dwellTimeMultiplier: 0.7 + trackedRandom() * 0.6,        // 0.7 - 1.3
    fidgetFrequencyMultiplier: 0.5 + trackedRandom(),        // 0.5 - 1.5
    overshootTendency: trackedRandom() * 0.3,                // 0 - 0.3 additional
    reReadTendency: trackedRandom() * 0.2                    // 0 - 0.2 additional
  };
}

/**
 * Apply session variation to persona
 */
function applySessionVariation(persona) {
  const v = persona.sessionVariation || generateSessionVariation();

  if (persona.mouse) {
    persona.mouse.fittsA = Math.round(persona.mouse.fittsA * v.mouseSpeedMultiplier);
    persona.mouse.fittsB = Math.round(persona.mouse.fittsB * v.mouseSpeedMultiplier);
    persona.mouse.overshootChance = Math.min(0.8, persona.mouse.overshootChance + v.overshootTendency);
  }

  if (persona.scroll) {
    persona.scroll.meanDistance = Math.round(persona.scroll.meanDistance * v.scrollSpeedMultiplier);
    persona.scroll.fidgetChance = Math.min(0.5, persona.scroll.fidgetChance * v.fidgetFrequencyMultiplier);
    persona.scroll.clickChance = Math.min(0.3, persona.scroll.clickChance * v.clickSpeedMultiplier);
    persona.scroll.reReadChance = Math.min(0.4, (persona.scroll.reReadChance || 0) + v.reReadTendency);
  }

  if (persona.click) {
    persona.click.preClickPause = Math.round(persona.click.preClickPause * v.clickSpeedMultiplier);
  }

  if (persona.dwell) {
    for (const key of Object.keys(persona.dwell)) {
      if (persona.dwell[key]?.scale) {
        persona.dwell[key].scale = Math.round(persona.dwell[key].scale * v.dwellTimeMultiplier);
      }
    }
  }

  if (persona.idle) {
    persona.idle.fidgetChance = Math.min(0.5, persona.idle.fidgetChance * v.fidgetFrequencyMultiplier);
  }

  persona.sessionVariation = v;
  return persona;
}

/**
 * Create persona from template with overrides
 */
function createPersonaFromTemplate(template, overrides = {}) {
  const base = { ...template };
  return deepMerge(base, overrides);
}

/**
 * Persona templates for common user types
 */
const PERSONA_TEMPLATES = {
  // E-commerce shopper
  shopper: {
    mode: 'normal',
    overrides: {
      scroll: { meanDistance: 350, clickChance: 0.08 },
      click: { preClickPause: 120 },
      dwell: { reading: { shape: 0.8, scale: 5000 } }
    }
  },

  // Content reader (blog, news)
  reader: {
    mode: 'careful',
    overrides: {
      scroll: { meanDistance: 200, reReadChance: 0.15 },
      dwell: { deepRead: { shape: 1.3, scale: 12000 } },
      idle: { fidgetChance: 0.08 }
    }
  },

  // Social media scroller
  social_scroller: {
    mode: 'fast',
    overrides: {
      scroll: { meanDistance: 600, fidgetChance: 0.15 },
      click: { preClickPause: 60 },
      idle: { fidgetChance: 0.2 }
    }
  },

  // Researcher/deep diver
  researcher: {
    mode: 'careful',
    overrides: {
      scroll: { meanDistance: 150, clickChance: 0.05, reReadChance: 0.2 },
      dwell: { deepRead: { shape: 1.4, scale: 15000 } },
      click: { preClickPause: 250 }
    }
  },

  // Casual browser
  casual: {
    mode: 'normal',
    overrides: {
      scroll: { meanDistance: 400 },
      idle: { fidgetChance: 0.12 }
    }
  },

  // Bot-like (for testing detection) - NOT for production use
  bot_like: {
    mode: 'fast',
    overrides: {
      mouse: { jitterStd: 0.1, overshootChance: 0 },
      scroll: { meanDistance: 500, distanceVariance: 0.1, fidgetChance: 0 },
      click: { preClickPause: 50, preClickVariance: 0 },
      idle: { fidgetChance: 0 },
      dwell: { reading: { shape: 2.0, scale: 1000 } } // Very consistent
    }
  }
};

/**
 * Get persona template
 */
function getPersonaTemplate(name) {
  const template = PERSONA_TEMPLATES[name];
  if (!template) {
    throw new Error(`Unknown persona template: ${name}. Available: ${Object.keys(PERSONA_TEMPLATES).join(', ')}`);
  }
  return createPersonaFromTemplate(
    getModeConfig(template.mode),
    template.overrides
  );
}

/**
 * List available persona templates
 */
function listPersonaTemplates() {
  return Object.keys(PERSONA_TEMPLATES);
}

/**
 * Validate persona configuration
 */
function validatePersona(persona) {
  const errors = [];
  const warnings = [];

  if (!persona.mouse) errors.push('Missing mouse configuration');
  if (!persona.scroll) errors.push('Missing scroll configuration');
  if (!persona.click) errors.push('Missing click configuration');
  if (!persona.idle) errors.push('Missing idle configuration');

  if (persona.mouse) {
    if (persona.mouse.fittsA < 50) warnings.push('fittsA very low - may appear robotic');
    if (persona.mouse.fittsA > 300) warnings.push('fittsA very high - extremely slow');
    if (persona.mouse.jitterStd < 0.5) warnings.push('jitterStd very low - no hand tremor');
    if (persona.mouse.jitterStd > 5) warnings.push('jitterStd very high - erratic movement');
    if (persona.mouse.overshootChance > 0.8) warnings.push('overshootChance very high');
  }

  if (persona.scroll) {
    if (persona.scroll.fidgetChance > 0.5) warnings.push('scroll fidgetChance very high');
    if (persona.scroll.meanDistance > 1000) warnings.push('meanDistance very large');
  }

  if (persona.idle) {
    if (persona.idle.fidgetChance > 0.5) warnings.push('idle fidgetChance very high');
  }

  return { valid: errors.length === 0, errors, warnings };
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
  generatePersona,
  generateEntropySeed,
  generateSessionVariation,
  applySessionVariation,
  createPersonaFromTemplate,
  getPersonaTemplate,
  listPersonaTemplates,
  validatePersona,
  PERSONA_TEMPLATES
};