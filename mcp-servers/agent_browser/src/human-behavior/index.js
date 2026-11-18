/**
 * human-behavior/index.js - Main exports for human behavior engine
 */

const mousePhysics = require('./mouse-physics');
const scrollMarkov = require('./scroll-markov');
const microHabits = require('./micro-habits');
const dwellWeibull = require('./dwell-weibull');
const sessionEngine = require('./session-engine');
const modePresets = require('./mode-presets');
const profiles = require('./profiles');
const mathUtils = require('./math-utils');

module.exports = {
  // Core modules
  mouse: mousePhysics,
  scroll: scrollMarkov,
  microHabits,
  dwell: dwellWeibull,
  session: sessionEngine,
  presets: modePresets,
  profiles,
  math: mathUtils,

  // Convenience exports
  humanMove: mousePhysics.humanMove,
  humanClick: mousePhysics.humanClick,
  humanHover: mousePhysics.humanHover,
  humanDragDrop: mousePhysics.humanDragDrop,
  humanScroll: scrollMarkov.humanScroll,
  humanDwell: scrollMarkov.humanDwell,
  idleFidget: microHabits.idleFidget,
  preClickSequence: microHabits.preClickSequence,
  postClickBehavior: microHabits.postClickBehavior,
  readingBehavior: microHabits.readingBehavior,
  pageOrientation: microHabits.pageOrientation,
  executePageview: sessionEngine.executePageview,
  runSession: sessionEngine.runSession,
  createPersona: profiles.generatePersona,
  getModeConfig: modePresets.getModeConfig,
  listModes: modePresets.listModes,
  getPersonaTemplate: profiles.getPersonaTemplate,
  listPersonaTemplates: profiles.listPersonaTemplates,
  validatePersona: profiles.validatePersona,
  trackedRandom: mathUtils.trackedRandom,
  gaussianRandom: mathUtils.gaussianRandom,
  sleep: mathUtils.sleep
};