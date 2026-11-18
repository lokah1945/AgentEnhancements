/**
 * persona.js - Persona configuration MCP tools
 */

const { getModeConfig, listModes, mergeWithPreset } = require('../human-behavior/mode-presets');
const { generatePersona, getPersonaTemplate, listPersonaTemplates, validatePersona } = require('../human-behavior/profiles');

/**
 * Set persona for session
 */
async function personaSet(args, context) {
  const { sessionId, persona, preset } = args;

  let finalPersona = persona;

  if (preset) {
    finalPersona = getModeConfig(preset);
  } else if (persona?.preset) {
    finalPersona = getModeConfig(persona.preset);
  }

  // Merge with custom overrides
  if (persona && !preset) {
    finalPersona = mergeWithPreset(finalPersona?.mode || 'normal', persona);
  }

  // Generate session variation
  const { generateSessionVariation, applySessionVariation } = require('../human-behavior/profiles');
  finalPersona.sessionVariation = generateSessionVariation();
  applySessionVariation(finalPersona);

  // Store in session (would need session storage)
  // For now, return the persona
  return {
    success: true,
    persona: finalPersona,
    applied: true
  };
}

/**
 * Get current persona
 */
async function personaGet(args, context) {
  const { sessionId } = args;

  // In real implementation, retrieve from session storage
  // For now, return default
  return {
    success: true,
    persona: getModeConfig('normal')
  };
}

/**
 * List available modes
 */
async function personaListModes(args, context) {
  return {
    success: true,
    modes: listModes()
  };
}

/**
 * List persona templates
 */
async function personaListTemplates(args, context) {
  return {
    success: true,
    templates: listPersonaTemplates()
  };
}

/**
 * Get persona template
 */
async function personaGetTemplate(args, context) {
  const { name } = args;

  try {
    const persona = getPersonaTemplate(name);
    return { success: true, persona };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

/**
 * Validate persona
 */
async function personaValidate(args, context) {
  const { persona } = args;

  const result = validatePersona(persona);
  return {
    success: true,
    ...result
  };
}

/**
 * Create persona from template
 */
async function personaCreate(args, context) {
  const { template, overrides } = args;

  try {
    const persona = getPersonaTemplate(template);

    if (overrides) {
      const { deepMerge } = require('../human-behavior/profiles');
      const merged = deepMerge(persona, overrides);
      const { applySessionVariation } = require('../human-behavior/profiles');
      merged.sessionVariation = generateSessionVariation();
      applySessionVariation(merged);
      return { success: true, persona: merged };
    }

    return { success: true, persona };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

module.exports = {
  personaSet,
  personaGet,
  personaListModes,
  personaListTemplates,
  personaGetTemplate,
  personaValidate,
  personaCreate
};