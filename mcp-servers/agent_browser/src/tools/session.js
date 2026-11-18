/**
 * session.js - Session management MCP tools
 */

const { SessionManager } = require('../session-manager');

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
  const session = await mgr.getSession(sessionId);

  return {
    success: true,
    session
  };
}

/**
 * Delete a session
 */
async function sessionDelete(args, context) {
  const { sessionId, force } = args;

  const mgr = getSessionManager();
  await mgr.deleteSession(sessionId, { force });

  return {
    success: true,
    sessionId
  };
}

/**
 * Snapshot session state
 */
async function sessionSnapshot(args, context) {
  const { sessionId, includeCookies, includeStorage, includeHistory } = args;

  const mgr = getSessionManager();
  const snapshot = await mgr.snapshotSession(sessionId, {
    includeCookies: includeCookies !== false,
    includeStorage: includeStorage !== false,
    includeHistory: includeHistory === true
  });

  return {
    success: true,
    snapshot
  };
}

/**
 * Restore session from snapshot
 */
async function sessionRestore(args, context) {
  const { snapshot, newSessionId } = args;

  const mgr = getSessionManager();
  const result = await mgr.restoreSession(snapshot, newSessionId);

  return {
    success: true,
    sessionId: result.sessionId,
    metadata: result.metadata,
    profilePath: result.profilePath
  };
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