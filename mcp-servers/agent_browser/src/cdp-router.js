/**
 * cdp-router.js - CDP connection management and routing
 *
 * Keeps one CDP session per tab (page) of a browser session. Pages get stable
 * ids assigned here (Playwright exposes none publicly), so lookups by id or by
 * 'default' (the active tab) always hit the cache instead of opening a new
 * CDP session and re-running the init scripts on every tool call.
 */

const crypto = require('crypto');
const { applyCDPEmulation, applyHeadlessDefense } = require('./launch-config');

class CDPRouter {
  constructor() {
    this.sessions = new Map(); // sessionId -> session state (see registerSession)
    this.pageIds = new WeakMap(); // Playwright Page -> stable page id
  }

  /**
   * Register a new browser session
   */
  registerSession(sessionId, { browser, context, defaultPage, emulationConfig }) {
    this.sessions.set(sessionId, {
      browser,
      context,
      pages: new Map(), // pageId -> { page, cdp, frameId, mainFrame }
      pending: new Map(), // pageId -> Promise<cdp> while a CDP session is being set up
      cdpClients: new Map(), // targetId -> cdpSession
      eventHandlers: [],
      defaultPage: defaultPage || null,
      activePage: null,
      emulationConfig: emulationConfig || null,
      tabCount: 0
    });
    console.error(`[CDPRouter] Registered session: ${sessionId}`);
  }

  /**
   * Get session data
   */
  getSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session) {
      throw new Error(`Session not found: ${sessionId}`);
    }
    return session;
  }

  /**
   * Stable id for a Playwright page, assigned on first sight.
   */
  getPageId(page) {
    let id = this.pageIds.get(page);
    if (!id) {
      id = `page_${crypto.randomUUID()}`;
      this.pageIds.set(page, id);
    }
    return id;
  }

  /** Open pages of the session, in the browser's tab order. */
  listOpenPages(session) {
    let pages = [];
    try {
      pages = session.context.pages();
    } catch (e) {
      pages = [];
    }
    return pages.filter((p) => !p.isClosed());
  }

  /** The page 'default' refers to: the active tab, else the first open tab. */
  resolveDefaultPage(session) {
    for (const candidate of [session.activePage, session.defaultPage]) {
      if (candidate && !candidate.isClosed()) return candidate;
    }
    const [first] = this.listOpenPages(session);
    if (first) session.defaultPage = first;
    return first || null;
  }

  /**
   * Find page by ID
   */
  findPageById(session, pageId) {
    const known = session.pages.get(pageId);
    if (known && !known.page.isClosed()) return known.page;
    return this.listOpenPages(session).find((p) => this.getPageId(p) === pageId) || null;
  }

  /**
   * Get (or create once) the CDP session for a page.
   */
  async getPageCDP(sessionId, pageId = 'default', emulationConfig = null) {
    const session = this.getSession(sessionId);
    const page = pageId === 'default' ? this.resolveDefaultPage(session) : this.findPageById(session, pageId);
    if (!page) {
      throw new Error(`Page not found: ${pageId}`);
    }
    const pid = this.getPageId(page);
    const existing = session.pages.get(pid);
    if (existing && existing.cdp) return existing.cdp;
    if (session.pending.has(pid)) return session.pending.get(pid);

    const setup = this.attachPage(session, page, pid, emulationConfig || session.emulationConfig);
    session.pending.set(pid, setup);
    try {
      return await setup;
    } finally {
      session.pending.delete(pid);
    }
  }

  /** Create and instrument the CDP session for one page and index it. */
  async attachPage(session, page, pid, emulationConfig) {
    const cdp = await session.context.newCDPSession(page);
    try {
      await this.enableRequiredDomains(cdp);
      if (emulationConfig) {
        await applyCDPEmulation(cdp, emulationConfig);
      }
      await applyHeadlessDefense(cdp);
      let frameId = null;
      try {
        const { frameTree } = await cdp.send('Page.getFrameTree');
        frameId = frameTree.frame.id;
      } catch (e) {
        console.error('[CDPRouter] Page.getFrameTree failed:', e.message);
      }
      session.pages.set(pid, { page, cdp, frameId, mainFrame: true });
      if (typeof page.once === 'function') {
        page.once('close', () => this.forgetPage(session, pid));
      }
      this.updateTabCount(session);
      return cdp;
    } catch (error) {
      try { await cdp.detach(); } catch (e) {}
      throw error;
    }
  }

  /** Drop a page from the index and release its CDP session and handlers. */
  forgetPage(session, pid) {
    const pageData = session.pages.get(pid);
    if (!pageData) return Promise.resolve();
    session.pages.delete(pid);
    session.eventHandlers = session.eventHandlers.filter((h) => {
      if (h.cdp !== pageData.cdp) return true;
      try { h.cdp.off(`${h.domain}.${h.event}`, h.handler); } catch (e) {}
      return false;
    });
    if (session.activePage === pageData.page) session.activePage = null;
    if (session.defaultPage === pageData.page) session.defaultPage = null;
    this.updateTabCount(session);
    return Promise.resolve()
      .then(() => pageData.cdp && pageData.cdp.detach())
      .catch(() => {});
  }

  /**
   * Enable required CDP domains
   * Note: Only page-level domains are enabled here.
   */
  async enableRequiredDomains(cdp) {
    const pageDomains = [
      'Page',
      'Runtime',
      'DOM',
      'Network',
      'Console',
      'Log',
      'Overlay',
      'Accessibility',
      'CSS',
      'DOMSnapshot'
    ];

    for (const domain of pageDomains) {
      try {
        await cdp.send(`${domain}.enable`);
      } catch (e) {
        console.error(`[CDPRouter] Domain ${domain} not available:`, e.message);
      }
    }
  }

  /**
   * Apply CDP emulation to a page (viewport, UA, timezone, etc.)
   */
  async applyEmulation(sessionId, pageId, config) {
    const cdp = await this.getPageCDP(sessionId, pageId);
    return applyCDPEmulation(cdp, config);
  }

  /** CDP session of the tab whose main frame is `frameId`. */
  async cdpForFrame(sessionId, frameId) {
    await this.getPageCDP(sessionId, 'default');
    const session = this.getSession(sessionId);
    for (const page of this.listOpenPages(session)) {
      await this.getPageCDP(sessionId, this.getPageId(page));
    }
    for (const pageData of session.pages.values()) {
      if (pageData.frameId === frameId) return pageData.cdp;
    }
    throw new Error(`Frame not found: ${frameId} (only tab main frames can be targeted)`);
  }

  /**
   * Send raw CDP command
   */
  async sendCDP(sessionId, domain, method, params, target = {}) {
    const session = this.getSession(sessionId);
    let cdp;
    if (target && target.frameId) {
      cdp = await this.cdpForFrame(sessionId, target.frameId);
    } else if (target && target.targetId && session.cdpClients.has(target.targetId)) {
      cdp = session.cdpClients.get(target.targetId);
    } else {
      cdp = await this.getPageCDP(sessionId, 'default');
    }
    return cdp.send(`${domain}.${method}`, params || {});
  }

  /**
   * Evaluate JavaScript in page context
   */
  async evaluate(sessionId, expression, options = {}) {
    const {
      awaitPromise = true,
      returnByValue = true,
      target = 'page',
      frameId = null
    } = options;

    const cdp = target === 'frame' && frameId
      ? await this.cdpForFrame(sessionId, frameId)
      : await this.getPageCDP(sessionId, 'default');

    const result = await cdp.send('Runtime.evaluate', {
      expression,
      awaitPromise,
      returnByValue,
      userGesture: true,
      generatePreview: false
    });

    if (result.exceptionDetails) {
      const detail = result.exceptionDetails.exception && result.exceptionDetails.exception.description;
      throw new Error(`JS Evaluation error: ${detail || result.exceptionDetails.text}`);
    }

    return result.result ? result.result.value : undefined;
  }

  /**
   * Subscribe to CDP events (logged to stderr; cdp_subscribe forwards them as
   * MCP notifications instead).
   */
  async subscribe(sessionId, domain, event) {
    const session = this.getSession(sessionId);
    const cdp = await this.getPageCDP(sessionId, 'default');
    const handler = (...args) => {
      console.error(`[CDPRouter] Event: ${domain}.${event}`, args[0]);
    };
    cdp.on(`${domain}.${event}`, handler);
    session.eventHandlers.push({ domain, event, handler, cdp });
    return { subscribed: true, domain, event };
  }

  /**
   * List the session's open tabs.
   */
  async getPages(sessionId) {
    const session = this.getSession(sessionId);
    const active = this.resolveDefaultPage(session);
    const pages = [];
    for (const page of this.listOpenPages(session)) {
      let title = '';
      try {
        title = await page.title();
      } catch (e) {}
      pages.push({
        pageId: this.getPageId(page),
        url: page.url(),
        title,
        isMainFrame: true,
        active: page === active
      });
    }
    return pages;
  }

  /**
   * Create new page/tab
   */
  async createPage(sessionId, url = 'about:blank') {
    const session = this.getSession(sessionId);
    const page = await session.context.newPage();
    const pid = this.getPageId(page);
    const cdp = await this.getPageCDP(sessionId, pid);

    if (url && url !== 'about:blank') {
      await page.goto(url, { waitUntil: 'domcontentloaded' });
    }

    return { pageId: pid, page, cdp };
  }

  /**
   * Switch to page (bring to front); it becomes the target of 'default'.
   */
  async bringToFront(sessionId, pageId) {
    const session = this.getSession(sessionId);
    const page = this.findPageById(session, pageId);
    if (!page) {
      throw new Error(`Page not found: ${pageId}`);
    }
    await page.bringToFront();
    session.activePage = page;
    return { success: true };
  }

  /**
   * Close a page, its CDP session and its event handlers
   */
  async closePage(sessionId, pageId) {
    const session = this.getSession(sessionId);
    const page = this.findPageById(session, pageId);
    if (!page) {
      throw new Error(`Page not found: ${pageId}`);
    }
    await this.forgetPage(session, this.getPageId(page));
    try {
      await page.close();
    } catch (e) {}
    return { success: true };
  }

  /**
   * Update the session's tab count
   */
  updateTabCount(sessionOrId) {
    const session = typeof sessionOrId === 'string' ? this.sessions.get(sessionOrId) : sessionOrId;
    if (session) {
      session.tabCount = session.pages.size;
    }
  }

  /**
   * Clean up session: handlers, CDP sessions, context and browser
   */
  async closeSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session) return;
    this.sessions.delete(sessionId);

    for (const { domain, event, handler, cdp } of session.eventHandlers) {
      try {
        cdp.off(`${domain}.${event}`, handler);
      } catch (e) {}
    }
    session.eventHandlers = [];

    for (const pageData of session.pages.values()) {
      try {
        if (pageData.cdp) await pageData.cdp.detach();
      } catch (e) {}
    }
    session.pages.clear();

    try {
      await session.context.close();
    } catch (e) {}
    if (session.browser && session.browser !== session.context) {
      try {
        await session.browser.close();
      } catch (e) {}
    }

    console.error(`[CDPRouter] Closed session: ${sessionId}`);
  }
}

module.exports = { CDPRouter };
