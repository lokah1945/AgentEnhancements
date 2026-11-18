/**
 * session-manager.js - Persistent browser profile management
 *
 * Handles session lifecycle: create, list, delete, snapshot, restore
 * Profiles stored in ~/.agent-browser/profiles/{sessionId}/
 */

const fs = require('fs');
const path = require('path');
const { homedir } = require('os');
const crypto = require('crypto');

const DEFAULT_PROFILE_ROOT = path.join(homedir(), '.agent-browser', 'profiles');
const SESSIONS_INDEX = path.join(DEFAULT_PROFILE_ROOT, 'sessions.json');

class SessionManager {
  constructor(options = {}) {
    this.profileRoot = options.profileRoot || DEFAULT_PROFILE_ROOT;
    this.ensureDirectories();
    this.sessions = this.loadSessionsIndex();
  }

  ensureDirectories() {
    if (!fs.existsSync(this.profileRoot)) {
      fs.mkdirSync(this.profileRoot, { recursive: true });
    }
  }

  loadSessionsIndex() {
    try {
      if (fs.existsSync(SESSIONS_INDEX)) {
        return JSON.parse(fs.readFileSync(SESSIONS_INDEX, 'utf8'));
      }
    } catch (e) {
      console.warn('[SessionManager] Failed to load sessions index:', e.message);
    }
    return {};
  }

  saveSessionsIndex() {
    try {
      fs.writeFileSync(SESSIONS_INDEX, JSON.stringify(this.sessions, null, 2), 'utf8');
    } catch (e) {
      console.error('[SessionManager] Failed to save sessions index:', e.message);
    }
  }

  generateSessionId() {
    return 'sess_' + crypto.randomBytes(12).toString('hex');
  }

  getProfilePath(sessionId) {
    return path.join(this.profileRoot, sessionId);
  }

  getSessionMetadata(sessionId) {
    return this.sessions[sessionId] || null;
  }

  async createSession(config = {}) {
    const sessionId = config.sessionId || this.generateSessionId();
    const persistent = config.persistent !== false;

    const profilePath = this.getProfilePath(sessionId);

    // Create profile directory if persistent
    if (persistent) {
      if (!fs.existsSync(profilePath)) {
        fs.mkdirSync(profilePath, { recursive: true });
      }
    }

    const metadata = {
      sessionId,
      createdAt: new Date().toISOString(),
      lastUsedAt: new Date().toISOString(),
      persistent,
      browser: config.browser || 'chrome',
      viewport: config.viewport || { width: 1920, height: 1080, deviceScaleFactor: 1, isMobile: false, hasTouch: false },
      locale: config.locale || 'en-US',
      timezone: config.timezone || 'America/New_York',
      proxy: config.proxy || null,
      profilePath: persistent ? profilePath : null,
      status: 'created',
      tabCount: 0
    };

    this.sessions[sessionId] = metadata;
    this.saveSessionsIndex();

    console.log(`[SessionManager] Created session: ${sessionId} (persistent: ${persistent})`);
    return { sessionId, metadata, profilePath };
  }

  async updateSession(sessionId, updates) {
    if (!this.sessions[sessionId]) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    this.sessions[sessionId] = {
      ...this.sessions[sessionId],
      ...updates,
      lastUsedAt: new Date().toISOString()
    };
    this.saveSessionsIndex();
    return this.sessions[sessionId];
  }

  async deleteSession(sessionId, options = {}) {
    const session = this.sessions[sessionId];
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }

    // Delete profile directory if persistent
    if (session.persistent && session.profilePath && fs.existsSync(session.profilePath)) {
      if (options.force || session.status === 'closed') {
        try {
          fs.rmSync(session.profilePath, { recursive: true, force: true });
          console.log(`[SessionManager] Deleted profile: ${session.profilePath}`);
        } catch (e) {
          console.warn('[SessionManager] Failed to delete profile:', e.message);
        }
      } else {
        throw new Error(`Session ${sessionId} is still active. Use force: true or close session first.`);
      }
    }

    delete this.sessions[sessionId];
    this.saveSessionsIndex();

    console.log(`[SessionManager] Deleted session: ${sessionId}`);
    return { success: true, sessionId };
  }

  async listSessions() {
    return Object.values(this.sessions).map(s => ({
      sessionId: s.sessionId,
      createdAt: s.createdAt,
      lastUsedAt: s.lastUsedAt,
      persistent: s.persistent,
      browser: s.browser,
      status: s.status,
      tabCount: s.tabCount,
      viewport: s.viewport
    }));
  }

  async getSession(sessionId) {
    const session = this.sessions[sessionId];
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }
    return session;
  }

  async snapshotSession(sessionId, options = {}) {
    const session = await this.getSession(sessionId);
    if (!session.persistent) {
      throw new Error('Cannot snapshot non-persistent session');
    }

    const profilePath = session.profilePath;
    const snapshot = {
      sessionId,
      timestamp: new Date().toISOString(),
      metadata: { ...session }
    };

    // Include cookies if requested
    if (options.includeCookies !== false) {
      snapshot.cookies = await this.extractCookies(profilePath);
    }

    // Include localStorage/IndexedDB if requested
    if (options.includeStorage !== false) {
      snapshot.storage = await this.extractStorage(profilePath);
    }

    // Include history if requested
    if (options.includeHistory) {
      snapshot.history = await this.extractHistory(profilePath);
    }

    return snapshot;
  }

  async extractCookies(profilePath) {
    // Cookies are in SQLite database - would need better-sqlite3
    // For now, return placeholder
    return { note: 'Cookies stored in SQLite - use CDP Network.getCookies for live access' };
  }

  async extractStorage(profilePath) {
    const storagePath = path.join(profilePath, 'Default', 'Local Storage');
    if (!fs.existsSync(storagePath)) {
      return { localStorage: {}, indexedDB: {} };
    }

    // LocalStorage files are .ldb (LevelDB) - complex to parse
    // Return placeholder
    return { note: 'LocalStorage/IndexedDB in LevelDB format - use CDP Storage APIs for live access' };
  }

  async extractHistory(profilePath) {
    // History is in SQLite database
    return { note: 'History stored in SQLite - use CDP for live access' };
  }

  async restoreSession(snapshot, newSessionId = null) {
    const sessionId = newSessionId || this.generateSessionId();
    const profilePath = this.getProfilePath(sessionId);

    fs.mkdirSync(profilePath, { recursive: true });

    const metadata = {
      sessionId,
      createdAt: new Date().toISOString(),
      lastUsedAt: new Date().toISOString(),
      persistent: true,
      browser: snapshot.metadata?.browser || 'chrome',
      viewport: snapshot.metadata?.viewport || { width: 1920, height: 1080 },
      locale: snapshot.metadata?.locale || 'en-US',
      timezone: snapshot.metadata?.timezone || 'America/New_York',
      profilePath,
      status: 'restored',
      tabCount: 0,
      restoredFrom: snapshot.sessionId,
      restoredAt: snapshot.timestamp
    };

    this.sessions[sessionId] = metadata;
    this.saveSessionsIndex();

    console.log(`[SessionManager] Restored session: ${sessionId} from ${snapshot.sessionId}`);
    return { sessionId, metadata, profilePath };
  }

  markSessionActive(sessionId) {
    if (this.sessions[sessionId]) {
      this.sessions[sessionId].status = 'active';
      this.sessions[sessionId].lastUsedAt = new Date().toISOString();
      this.saveSessionsIndex();
    }
  }

  markSessionClosed(sessionId) {
    if (this.sessions[sessionId]) {
      this.sessions[sessionId].status = 'closed';
      this.sessions[sessionId].lastUsedAt = new Date().toISOString();
      this.saveSessionsIndex();
    }
  }

  updateTabCount(sessionId, count) {
    if (this.sessions[sessionId]) {
      this.sessions[sessionId].tabCount = count;
      this.saveSessionsIndex();
    }
  }

  cleanupOrphanedProfiles() {
    try {
      const dirs = fs.readdirSync(this.profileRoot);
      let cleaned = 0;

      for (const dir of dirs) {
        if (dir === 'sessions.json') continue;
        const fullPath = path.join(this.profileRoot, dir);
        if (!this.sessions[dir]) {
          try {
            fs.rmSync(fullPath, { recursive: true, force: true });
            cleaned++;
            console.log(`[SessionManager] Cleaned orphaned profile: ${dir}`);
          } catch (e) {
            console.warn(`[SessionManager] Failed to clean ${dir}:`, e.message);
          }
        }
      }

      return { cleaned };
    } catch (e) {
      console.error('[SessionManager] Cleanup failed:', e.message);
      return { error: e.message };
    }
  }
}

module.exports = { SessionManager, DEFAULT_PROFILE_ROOT };