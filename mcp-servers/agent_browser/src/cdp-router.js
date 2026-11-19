/**
 * cdp-router.js - CDP connection management and routing
 *
 * Manages CDP sessions for pages, frames, workers, and iframes
 * Handles auto-attachment for iframes/workers (Sentinel pattern)
 */

const { buildCDPEmulationConfig, applyCDPEmulation, applyHeadlessDefense } = require('./launch-config');

class CDPRouter {
  constructor() {
    this.sessions = new Map(); // sessionId -> { browser, context, pages, cdpClients, pageListeners }
  }

  /**
   * Register a new browser session
   */
  registerSession(sessionId, { browser, context, defaultPage, emulationConfig }) {
    this.sessions.set(sessionId, {
      browser,
      context,
      pages: new Map(), // pageId -> { page, cdp, frameId, mainFrame }
      cdpClients: new Map(), // targetId -> cdpSession
      pageListeners: new Set(),
      defaultPage: defaultPage,
      emulationConfig: emulationConfig // Store for applying to new pages
    });
    console.log(`[CDPRouter] Registered session: ${sessionId}`);
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
   * Get or create CDP session for a page
   */
  async getPageCDP(sessionId, pageId = 'default', emulationConfig = null) {
    const session = this.getSession(sessionId);
    const pageData = session.pages.get(pageId);

    if (pageData?.cdp) {
      return pageData.cdp;
    }

    // Find page by ID or use default
    let page;
    if (pageId !== 'default') {
      page = this.findPageById(session, pageId);
    } else {
      page = session.defaultPage || session.context.pages()[0];
    }

    if (!page) {
      throw new Error(`Page not found: ${pageId}`);
    }

    // Create CDP session
    const cdp = await session.context.newCDPSession(page);

    // Enable required domains
    await this.enableRequiredDomains(cdp);

    // Use provided emulationConfig or fall back to session's stored config
    const effectiveEmulationConfig = emulationConfig || session.emulationConfig;
    if (effectiveEmulationConfig) {
      await applyCDPEmulation(cdp, effectiveEmulationConfig);
    }

    // Apply headless defense to new page session
    await applyHeadlessDefense(cdp);

    // Store
    const pid = this.getPageId(page);
    session.pages.set(pid, { page, cdp, frameId: page.mainFrame()._id, mainFrame: true });

    return cdp;
  }

  /**
   * Enable required CDP domains
   * Note: Only page-level domains are enabled here.
   * Browser-level domains (Target, Browser, etc.) require a browser-level CDP session.
   */
  async enableRequiredDomains(cdp) {
    // Domains available on page-level CDP sessions
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

    // Domains that require browser-level session (handled separately if needed)
    // 'Input' - use Input.dispatchMouseEvent directly without enable
    // 'Target' - browser level only
    // 'Emulation' - handled by Playwright launch options + applyCDPEmulation
    // 'Storage' - may not be available on all targets
    // 'ServiceWorker' - browser level only

    for (const domain of pageDomains) {
      try {
        await cdp.send(`${domain}.enable`);
      } catch (e) {
        console.debug(`[CDPRouter] Domain ${domain} not available:`, e.message);
      }
    }

    // Input domain: commands work without explicit enable on page sessions
    // Emulation: applied via applyCDPEmulation() after this
    // Target.autoAttach: requires browser-level session (see setupAutoAttach)

    // Set up auto-attach for iframes/workers (requires browser-level session)
    // This will be called with browser-level session separately
    // await this.setupAutoAttach(cdp); // Moved to initializeBrowser with browser session
  }

  /**
   * Setup Target.autoAttach for iframe/worker coverage (Sentinel pattern)
   */
  async setupAutoAttach(cdp) {
    try {
      await cdp.send('Target.setAutoAttach', {
        autoAttach: true,
        waitForDebuggerOnStart: true, // Pause child targets before ANY JS executes
        flatten: true, // All nested frames accessible from this session
        // Only attach to these target types
        // Note: '*' attaches to all, but we can filter
      });

      // Handle attached targets
      cdp.on('Target.attachedToTarget', async ({ sessionId, targetInfo, waitingForDebugger }) => {
        console.log(`[CDPRouter] Target attached: ${targetInfo.type} - ${targetInfo.url?.substring(0, 80)}`);

        try {
          const childSession = await cdp.session({ sessionId });

          // Enable domains on child
          await this.enableRequiredDomains(childSession);

          // Apply headless defense to child
          await applyHeadlessDefense(childSession);

          // Apply emulation to child
          // Note: Child inherits parent's emulation but we reinforce

          // Resume if waiting
          if (waitingForDebugger) {
            await childSession.send('Runtime.runIfWaitingForDebugger');
          }

          console.log(`[CDPRouter] Child target instrumented: ${targetInfo.type}`);
        } catch (e) {
          console.warn('[CDPRouter] Failed to instrument child target:', e.message);
          // Still try to resume
          if (waitingForDebugger) {
            try {
              await cdp.send('Runtime.runIfWaitingForDebugger', {}, sessionId);
            } catch (e2) {}
          }
        }
      });

      console.log('[CDPRouter] Auto-attach configured (iframe + worker + SW + shared_worker)');
    } catch (e) {
      console.warn('[CDPRouter] Auto-attach setup failed:', e.message);
    }
  }

  /**
   * Apply CDP emulation to a page (viewport, UA, timezone, etc.)
   */
  async applyEmulation(sessionId, pageId, config) {
    const cdp = await this.getPageCDP(sessionId, pageId);
    return applyCDPEmulation(cdp, config);
  }

  /**
   * Send raw CDP command
   */
  async sendCDP(sessionId, domain, method, params, target = {}) {
    const session = this.getSession(sessionId);

    let cdp = session.cdpClients.get('main') || await this.getPageCDP(sessionId, 'default');

    // If targeting specific frame/worker
    if (target.frameId) {
      // Find CDP session for frame
      for (const [pid, pageData] of session.pages) {
        if (pageData.frameId === target.frameId) {
          cdp = pageData.cdp;
          break;
        }
      }
    } else if (target.targetId) {
      cdp = session.cdpClients.get(target.targetId) || cdp;
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

    const session = this.getSession(sessionId);

    let cdp = await this.getPageCDP(sessionId, 'default');

    if (target === 'frame' && frameId) {
      for (const [pid, pageData] of session.pages) {
        if (pageData.frameId === frameId) {
          cdp = pageData.cdp;
          break;
        }
      }
    }

    const result = await cdp.send('Runtime.evaluate', {
      expression,
      awaitPromise,
      returnByValue,
      userGesture: true,
      generatePreview: false
    });

    if (result.exceptionDetails) {
      throw new Error(`JS Evaluation error: ${result.exceptionDetails.text}`);
    }

    return result.result?.value;
  }

  /**
   * Subscribe to CDP events
   */
  async subscribe(sessionId, domain, event, callback) {
    const session = this.getSession(sessionId);
    const cdp = await this.getPageCDP(sessionId, 'default');

    const handler = (...args) => {
      // Callback would be handled via MCP notification system
      console.log(`[CDPRouter] Event: ${domain}.${event}`, args[0]);
    };

    cdp.on(`${domain}.${event}`, handler);

    // Store handler for cleanup
    if (!session.eventHandlers) session.eventHandlers = [];
    session.eventHandlers.push({ domain, event, handler, cdp });

    return { subscribed: true, domain, event };
  }

  /**
   * Get all pages in session
   */
  getPages(sessionId) {
    const session = this.getSession(sessionId);
    const pages = [];

    for (const [pid, pageData] of session.pages) {
      pages.push({
        pageId: pid,
        url: pageData.page.url(),
        title: pageData.page.title(),
        isMainFrame: pageData.mainFrame
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

    if (url !== 'about:blank') {
      await page.goto(url, { waitUntil: 'domcontentloaded' });
    }

    const pid = this.getPageId(page);
    const cdp = await session.context.newCDPSession(page);
    await this.enableRequiredDomains(cdp);

    // Apply emulation and defense to new page
    if (session.emulationConfig) {
      await applyCDPEmulation(cdp, session.emulationConfig);
    }
    await applyHeadlessDefense(cdp);

    session.pages.set(pid, { page, cdp, frameId: page.mainFrame()._id, mainFrame: true });

    // Update tab count
    this.updateTabCount(sessionId);

    return { pageId: pid, page, cdp };
  }

  /**
   * Close page
   */
  async closePage(sessionId, pageId) {
    const session = this.getSession(sessionId);
    const pageData = session.pages.get(pageId);

    if (pageData) {
      await pageData.page.close();
      session.pages.delete(pageId);
      this.updateTabCount(sessionId);
      return { success: true };
    }

    throw new Error(`Page not found: ${pageId}`);
  }

  /**
   * Switch to page (bring to front)
   */
  async bringToFront(sessionId, pageId) {
    const session = this.getSession(sessionId);
    const pageData = session.pages.get(pageId);

    if (pageData) {
      await pageData.page.bringToFront();
      return { success: true };
    }

    throw new Error(`Page not found: ${pageId}`);
  }

  /**
   * Get page ID from page object
   */
  getPageId(page) {
    // Generate stable page ID - use frame ID if available, otherwise generate UUID
    const frame = page.mainFrame();
    if (frame._id) {
      return frame._id;
    }
    // Fallback: generate unique ID based on page GUID or timestamp
    return `page_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Find page by ID
   */
  findPageById(session, pageId) {
    const pageData = session.pages.get(pageId);
    return pageData?.page;
  }

  /**
   * Update tab count in session manager
   */
  updateTabCount(sessionId) {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.tabCount = session.pages.size;
    }
  }

  /**
   * Clean up session
   */
  async closeSession(sessionId) {
    const session = this.sessions.get(sessionId);
    if (!session) return;

    // Clean up event handlers (subscriptions)
    if (session.eventHandlers) {
      for (const { domain, event, handler, cdp } of session.eventHandlers) {
        try {
          cdp.off(`${domain}.${event}`, handler);
        } catch (e) {}
      }
      session.eventHandlers = [];
    }

    // Close all page CDP sessions
    for (const [pid, pageData] of session.pages) {
      try {
        if (pageData.cdp) {
          await pageData.cdp.detach();
        }
      } catch (e) {}
      try {
        await pageData.page.close();
      } catch (e) {}
    }

    // Close context
    try {
      await session.context.close();
    } catch (e) {}

    // Close browser
    try {
      await session.browser.close();
    } catch (e) {}

    this.sessions.delete(sessionId);
    console.log(`[CDPRouter] Closed session: ${sessionId}`);
  }

  /**
   * Clean up page CDP session and event handlers
   */
  async closePage(sessionId, pageId) {
    const session = this.getSession(sessionId);
    const pageData = session.pages.get(pageId);

    if (pageData) {
      // Clean up event handlers for this page's CDP
      if (session.eventHandlers) {
        session.eventHandlers = session.eventHandlers.filter(h => h.cdp !== pageData.cdp);
      }
      try {
        if (pageData.cdp) {
          await pageData.cdp.detach();
        }
      } catch (e) {}
      try {
        await pageData.page.close();
      } catch (e) {}
      session.pages.delete(pageId);
      this.updateTabCount(sessionId);
      return { success: true };
    }

    throw new Error(`Page not found: ${pageId}`);
  }

  /**
   * Get CDP session for a specific target (frame, worker, iframe)
   */
  async getTargetCDP(sessionId, targetType, targetId = null) {
    const session = this.getSession(sessionId);

    if (targetType === 'page') {
      return this.getPageCDP(sessionId, 'default');
    }

    // For frames/workers, we need to find the target
    // This is handled by Target.setAutoAttach above
    // We can also use Target.getTargets to find specific targets

    const targets = await session.cdpClients.get('main')?.send('Target.getTargets');
    if (targets) {
      const target = targets.targetInfos.find(t => t.type === targetType && (!targetId || t.targetId === targetId));
      if (target) {
        // Check if we already have a session
        let cdp = session.cdpClients.get(target.targetId);
        if (!cdp) {
          cdp = await session.context.newCDPSession(session.pages.values().next().value?.page);
          await cdp.send('Target.attachToTarget', { targetId: target.targetId, flatten: true });
          session.cdpClients.set(target.targetId, cdp);
        }
        return cdp;
      }
    }

    throw new Error(`Target not found: ${targetType}${targetId ? ` ${targetId}` : ''}`);
  }
}

module.exports = { CDPRouter };