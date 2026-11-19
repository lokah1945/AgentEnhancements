/**
 * session.js - Session management MCP tools
 */

const { SessionManager } = require('../session-manager');
const { getCDPRouter } = require('../cdp-router-wrapper');
const { sessionNotFound, withErrorHandling } = require('../errors');

let sessionManager = null;

function getSessionManager() {
  if (!sessionManager) {
    sessionManager = new SessionManager();
  }
  return sessionManager;
}

/**
 * Create a new browser session
 */
async function sessionCreate(args, context) {
  const { sessionId, persistent, browser, profileDir, viewport, locale, timezone, proxy } = args;

  const mgr = getSessionManager();
  const result = await mgr.createSession({
    sessionId,
    persistent: persistent !== false,
    browser: browser || 'chrome',
    profileDir,
    viewport: viewport || { width: 1920, height: 1080, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
    locale: locale || 'en-US',
    timezone: timezone || 'America/New_York',
    proxy
  });

  return {
    success: true,
    sessionId: result.sessionId,
    metadata: result.metadata,
    profilePath: result.profilePath
  };
}

/**
 * List all sessions
 */
async function sessionList(args, context) {
  const mgr = getSessionManager();
  const sessions = await mgr.listSessions();

  return {
    success: true,
    sessions,
    count: sessions.length
  };
}

/**
 * Get session details
 */
async function sessionGet(args, context) {
  const { sessionId } = args;

  const mgr = getSessionManager();
  try {
    const session = await mgr.getSession(sessionId);
    return { success: true, session };
  } catch (error) {
    if (error.message.includes('not found')) {
      return sessionNotFound(sessionId);
    }
    throw error;
  }
}

/**
 * Delete a session
 */
async function sessionDelete(args, context) {
  const { sessionId, force } = args;

  const mgr = getSessionManager();
  try {
    await mgr.deleteSession(sessionId, { force });
    return { success: true, sessionId };
  } catch (error) {
    if (error.message.includes('not found')) {
      return sessionNotFound(sessionId);
    }
    throw error;
  }
}

/**
 * Snapshot session state
 */
async function sessionSnapshot(args, context) {
  const { sessionId, includeCookies, includeStorage, includeHistory } = args;

  const mgr = getSessionManager();
  const router = getCDPRouter();
  try {
    const snapshot = await mgr.snapshotSession(sessionId, {
      includeCookies: includeCookies !== false,
      includeStorage: includeStorage !== false,
      includeHistory: includeHistory === true
    }, router);
    return { success: true, snapshot };
  } catch (error) {
    if (error.message.includes('not found')) {
      return sessionNotFound(sessionId);
    }
    throw error;
  }
}

/**
 * Restore session from snapshot
 */
async function sessionRestore(args, context) {
  const { snapshot, newSessionId } = args;

  const mgr = getSessionManager();
  try {
    const result = await mgr.restoreSession(snapshot, newSessionId);
    return {
      success: true,
      sessionId: result.sessionId,
      metadata: result.metadata,
      profilePath: result.profilePath
    };
  } catch (error) {
    if (error.message.includes('not found')) {
      return sessionNotFound(snapshot?.sessionId || 'unknown');
    }
    throw error;
  }
}

/**
 * Cleanup orphaned profiles
 */
async function sessionCleanup(args, context) {
  const mgr = getSessionManager();
  const result = mgr.cleanupOrphanedProfiles();

  return {
    success: true,
    ...result
  };
}

module.exports = {
  sessionCreate,
  sessionList,
  sessionGet,
  sessionDelete,
  sessionSnapshot,
  sessionRestore,
  sessionCleanup,
  getSessionManager
};