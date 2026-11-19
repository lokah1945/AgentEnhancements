/**
 * agent_browser MCP Server - Pure CDP browser automation
 */
const http = require('http');
const EventEmitter = require('events');
const {
  initializeBrowser,
  closeBrowser,
  getPageCDP,
  createPage,
  switchTab,
  closePage,
  listPages,
  sendCDP,
  evaluate,
  subscribe,
  getSessionManagerInstance,
  activeBrowsers
} = require('./cdp-router-wrapper');

/**
 * Notification manager for MCP server-to-client notifications
 */
class NotificationManager extends EventEmitter {
  constructor() {
    super();
    this.notificationCallbacks = new Map(); // sessionId -> callback
  }

  /**
   * Register a notification callback for a session
   */
  registerSessionCallback(sessionId, callback) {
    this.notificationCallbacks.set(sessionId, callback);
  }

  /**
   * Unregister notification callback
   */
  unregisterSessionCallback(sessionId) {
    this.notificationCallbacks.delete(sessionId);
  }

  /**
   * Send notification to client for a specific session
   */
  sendNotification(sessionId, method, params) {
    const callback = this.notificationCallbacks.get(sessionId);
    if (callback) {
      try {
        callback({ method, params });
      } catch (e) {
        console.error('[NotificationManager] Callback error:', e.message);
      }
    }
    // Also emit for any global listeners
    this.emit('notification', { sessionId, method, params });
  }

  /**
   * Broadcast notification to all sessions
   */
  broadcastNotification(method, params) {
    for (const [sessionId, callback] of this.notificationCallbacks) {
      try {
        callback({ method, params });
      } catch (e) {
        console.error('[NotificationManager] Broadcast callback error:', e.message);
      }
    }
  }
}

// Global notification manager
const notificationManager = new NotificationManager();

/**
 * Set the notification callback for stdio transport
 * This is called when the server starts
 */
function setNotificationCallback(callback) {
  // Global callback for all sessions (stdio mode)
  notificationManager.on('notification', callback);
}

function getNotificationManager() {
  return notificationManager;
}

const sessionTools = require('./tools/session');
const navigationTools = require('./tools/navigation');
const tabsTools = require('./tools/tabs');
const interactionTools = require('./tools/interaction');
const cdpDirectTools = require('./tools/cdp-direct');
const extractionTools = require('./tools/extraction');
const observationTools = require('./tools/observation');
const personaTools = require('./tools/persona');

const TOOLS = {
  session_create: sessionTools.sessionCreate,
  session_list: sessionTools.sessionList,
  session_get: sessionTools.sessionGet,
  session_delete: sessionTools.sessionDelete,
  session_snapshot: sessionTools.sessionSnapshot,
  session_restore: sessionTools.sessionRestore,
  session_cleanup: sessionTools.sessionCleanup,

  navigate: navigationTools.navigate,
  go_back: navigationTools.goBack,
  go_forward: navigationTools.goForward,
  reload: navigationTools.reload,
  get_current_url: navigationTools.getCurrentUrl,

  tab_new: tabsTools.tabNew,
  tab_switch: tabsTools.tabSwitch,
  tab_close: tabsTools.tabClose,
  tab_list: tabsTools.tabList,
  tab_get: tabsTools.tabGet,

  click: interactionTools.click,
  type: interactionTools.type,
  hover: interactionTools.hover,
  scroll: interactionTools.scroll,
  drag_drop: interactionTools.dragDrop,
  key_press: interactionTools.keyPress,

  cdp_send: cdpDirectTools.cdpSend,
  cdp_evaluate: cdpDirectTools.cdpEvaluate,
  cdp_subscribe: cdpDirectTools.cdpSubscribe,
  cdp_unsubscribe: cdpDirectTools.cdpUnsubscribe,
  cdp_network_capture: cdpDirectTools.cdpNetworkCapture,
  cdp_console_capture: cdpDirectTools.cdpConsoleCapture,
  cdp_capture_stop: cdpDirectTools.cdpCaptureStop,
  cdp_capture_get: cdpDirectTools.cdpCaptureGet,
  cdp_capture_list: cdpDirectTools.cdpCaptureList,
  cdp_metrics: cdpDirectTools.cdpMetrics,

  extract: extractionTools.extract,
  get_attributes: extractionTools.getAttributes,
  get_page_content: extractionTools.getPageContent,

  screenshot: observationTools.screenshot,
  pdf: observationTools.pdf,
  dom_snapshot: observationTools.domSnapshot,
  get_html: observationTools.getHTML,
  get_text: observationTools.getText,

  persona_set: personaTools.personaSet,
  persona_get: personaTools.personaGet,
  persona_list_modes: personaTools.personaListModes,
  persona_list_templates: personaTools.personaListTemplates,
  persona_get_template: personaTools.personaGetTemplate,
  persona_validate: personaTools.personaValidate,
  persona_create: personaTools.personaCreate
};

const TOOL_SCHEMAS = {
  "session_create": {
    "name": "session_create",
    "description": "Create a new persistent browser session (headless but indistinguishable from headful)",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string",
          "description": "Optional custom session ID"
        },
        "persistent": {
          "type": "boolean",
          "default": true
        },
        "browser": {
          "type": "string",
          "enum": [
            "chrome",
            "edge",
            "chromium"
          ],
          "default": "chrome"
        },
        "profileDir": {
          "type": "string"
        },
        "viewport": {
          "type": "object",
          "properties": {
            "width": {
              "type": "number",
              "default": 1920
            },
            "height": {
              "type": "number",
              "default": 1080
            },
            "deviceScaleFactor": {
              "type": "number",
              "default": 1
            },
            "isMobile": {
              "type": "boolean",
              "default": false
            },
            "hasTouch": {
              "type": "boolean",
              "default": false
            }
          }
        },
        "locale": {
          "type": "string",
          "default": "en-US"
        },
        "timezone": {
          "type": "string",
          "default": "America/New_York"
        },
        "proxy": {
          "type": "object",
          "properties": {
            "server": {
              "type": "string"
            },
            "bypass": {
              "type": "string"
            }
          }
        }
      }
    }
  },
  "session_list": {
    "name": "session_list",
    "description": "List all persisted browser sessions",
    "inputSchema": {
      "type": "object",
      "properties": {}
    }
  },
  "session_get": {
    "name": "session_get",
    "description": "Get session details",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "session_delete": {
    "name": "session_delete",
    "description": "Delete session and its profile",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "force": {
          "type": "boolean"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "session_snapshot": {
    "name": "session_snapshot",
    "description": "Export session state",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "includeCookies": {
          "type": "boolean",
          "default": true
        },
        "includeStorage": {
          "type": "boolean",
          "default": true
        },
        "includeHistory": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "session_restore": {
    "name": "session_restore",
    "description": "Restore session from snapshot",
    "inputSchema": {
      "type": "object",
      "properties": {
        "snapshot": {
          "type": "object"
        },
        "newSessionId": {
          "type": "string"
        }
      },
      "required": [
        "snapshot"
      ]
    }
  },
  "session_cleanup": {
    "name": "session_cleanup",
    "description": "Cleanup orphaned profile directories",
    "inputSchema": {
      "type": "object",
      "properties": {}
    }
  },
  "navigate": {
    "name": "navigate",
    "description": "Navigate to URL via CDP",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "url": {
          "type": "string"
        },
        "waitUntil": {
          "type": "string",
          "enum": [
            "domContentLoaded",
            "load",
            "networkIdle"
          ],
          "default": "domContentLoaded"
        },
        "referrer": {
          "type": "string"
        },
        "headers": {
          "type": "object"
        }
      },
      "required": [
        "sessionId",
        "url"
      ]
    }
  },
  "go_back": {
    "name": "go_back",
    "description": "Navigate back",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "go_forward": {
    "name": "go_forward",
    "description": "Navigate forward",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "reload": {
    "name": "reload",
    "description": "Reload page",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "ignoreCache": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "get_current_url": {
    "name": "get_current_url",
    "description": "Get current page URL and title",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "tab_new": {
    "name": "tab_new",
    "description": "Create new tab",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "url": {
          "type": "string",
          "default": "about:blank"
        },
        "background": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "tab_switch": {
    "name": "tab_switch",
    "description": "Switch active tab",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "tabIndex": {
          "type": "number"
        },
        "tabId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "tab_close": {
    "name": "tab_close",
    "description": "Close tab",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "tabIndex": {
          "type": "number"
        }
      },
      "required": [
        "sessionId",
        "tabIndex"
      ]
    }
  },
  "tab_list": {
    "name": "tab_list",
    "description": "List all tabs",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "tab_get": {
    "name": "tab_get",
    "description": "Get tab info",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "tabIndex": {
          "type": "number"
        },
        "tabId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "click": {
    "name": "click",
    "description": "Click with Fitts's Law human-like mouse movement",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "selector": {
          "type": "string"
        },
        "xpath": {
          "type": "string"
        },
        "position": {
          "type": "object",
          "properties": {
            "x": {
              "type": "number"
            },
            "y": {
              "type": "number"
            }
          }
        },
        "button": {
          "type": "string",
          "enum": [
            "left",
            "right",
            "middle"
          ],
          "default": "left"
        },
        "clickCount": {
          "type": "integer",
          "default": 1
        },
        "modifiers": {
          "type": "array",
          "items": {
            "type": "string",
            "enum": [
              "Alt",
              "Control",
              "Meta",
              "Shift"
            ]
          }
        },
        "humanize": {
          "type": "boolean",
          "default": true
        },
        "persona": {
          "type": "object"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "type": {
    "name": "type",
    "description": "Type text with human-like keystroke timing",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "selector": {
          "type": "string"
        },
        "xpath": {
          "type": "string"
        },
        "text": {
          "type": "string"
        },
        "clearFirst": {
          "type": "boolean",
          "default": true
        },
        "typingSpeed": {
          "type": "string",
          "enum": [
            "slow",
            "normal",
            "fast"
          ],
          "default": "normal"
        },
        "errorRate": {
          "type": "number",
          "default": 0.02
        },
        "humanize": {
          "type": "boolean",
          "default": true
        }
      },
      "required": [
        "sessionId",
        "text"
      ]
    }
  },
  "hover": {
    "name": "hover",
    "description": "Hover element with natural approach",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "selector": {
          "type": "string"
        },
        "xpath": {
          "type": "string"
        },
        "position": {
          "type": "object",
          "properties": {
            "x": {
              "type": "number"
            },
            "y": {
              "type": "number"
            }
          }
        },
        "duration": {
          "type": "number"
        },
        "humanize": {
          "type": "boolean",
          "default": true
        },
        "persona": {
          "type": "object"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "scroll": {
    "name": "scroll",
    "description": "Scroll with variable velocity + dwell pauses",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "direction": {
          "type": "string",
          "enum": [
            "down",
            "up",
            "left",
            "right"
          ],
          "default": "down"
        },
        "distance": {
          "type": "number"
        },
        "selector": {
          "type": "string"
        },
        "humanize": {
          "type": "boolean",
          "default": true
        },
        "persona": {
          "type": "object"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "drag_drop": {
    "name": "drag_drop",
    "description": "Drag and drop with Bezier path",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "sourceSelector": {
          "type": "string"
        },
        "sourceXpath": {
          "type": "string"
        },
        "targetSelector": {
          "type": "string"
        },
        "targetXpath": {
          "type": "string"
        },
        "humanize": {
          "type": "boolean",
          "default": true
        },
        "persona": {
          "type": "object"
        }
      },
      "required": [
        "sessionId",
        "sourceSelector",
        "targetSelector"
      ]
    }
  },
  "key_press": {
    "name": "key_press",
    "description": "Press key combination",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "key": {
          "type": "string"
        },
        "modifiers": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "text": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "cdp_send": {
    "name": "cdp_send",
    "description": "Send raw CDP command",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "domain": {
          "type": "string"
        },
        "method": {
          "type": "string"
        },
        "params": {
          "type": "object"
        },
        "target": {
          "type": "string",
          "enum": [
            "page",
            "frame",
            "worker",
            "iframe"
          ],
          "default": "page"
        },
        "frameId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId",
        "domain",
        "method"
      ]
    }
  },
  "cdp_evaluate": {
    "name": "cdp_evaluate",
    "description": "Evaluate JavaScript in page context",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "expression": {
          "type": "string"
        },
        "awaitPromise": {
          "type": "boolean",
          "default": true
        },
        "returnByValue": {
          "type": "boolean",
          "default": true
        },
        "target": {
          "type": "string",
          "enum": [
            "page",
            "frame",
            "worker"
          ],
          "default": "page"
        },
        "frameId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId",
        "expression"
      ]
    }
  },
  "cdp_subscribe": {
    "name": "cdp_subscribe",
    "description": "Subscribe to CDP events",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "domain": {
          "type": "string"
        },
        "event": {
          "type": "string"
        },
        "filter": {
          "type": "object"
        }
      },
      "required": [
        "sessionId",
        "domain",
        "event"
      ]
    }
  },
  "cdp_network_capture": {
    "name": "cdp_network_capture",
    "description": "Capture network traffic",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "filter": {
          "type": "object",
          "properties": {
            "urlPattern": {
              "type": "string"
            },
            "method": {
              "type": "string"
            },
            "resourceType": {
              "type": "string"
            }
          }
        },
        "maxEntries": {
          "type": "integer",
          "default": 500
        },
        "includeBody": {
          "type": "boolean",
          "default": true
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "cdp_console_capture": {
    "name": "cdp_console_capture",
    "description": "Capture console messages",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "maxEntries": {
          "type": "integer",
          "default": 200
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "cdp_metrics": {
    "name": "cdp_metrics",
    "description": "Get page performance metrics",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "cdp_unsubscribe": {
    "name": "cdp_unsubscribe",
    "description": "Unsubscribe from CDP events",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "subscriptionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId",
        "subscriptionId"
      ]
    }
  },
  "cdp_capture_stop": {
    "name": "cdp_capture_stop",
    "description": "Stop a network or console capture and get entries",
    "inputSchema": {
      "type": "object",
      "properties": {
        "captureId": {
          "type": "string"
        }
      },
      "required": [
        "captureId"
      ]
    }
  },
  "cdp_capture_get": {
    "name": "cdp_capture_get",
    "description": "Get capture entries without stopping",
    "inputSchema": {
      "type": "object",
      "properties": {
        "captureId": {
          "type": "string"
        }
      },
      "required": [
        "captureId"
      ]
    }
  },
  "cdp_capture_list": {
    "name": "cdp_capture_list",
    "description": "List active captures",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      }
    }
  },
  "extract": {
    "name": "extract",
    "description": "Extract data via multiple strategies",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "selector": {
          "type": "string"
        },
        "xpath": {
          "type": "string"
        },
        "attribute": {
          "type": "string"
        },
        "script": {
          "type": "string"
        },
        "multiple": {
          "type": "boolean",
          "default": false
        },
        "format": {
          "type": "string",
          "enum": [
            "text",
            "html",
            "json",
            "markdown",
            "structured"
          ],
          "default": "text"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "get_attributes": {
    "name": "get_attributes",
    "description": "Get element attributes",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "selector": {
          "type": "string"
        },
        "xpath": {
          "type": "string"
        },
        "attributes": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "get_page_content": {
    "name": "get_page_content",
    "description": "Get full page content",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "format": {
          "type": "string",
          "enum": [
            "html",
            "text",
            "markdown"
          ],
          "default": "html"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "screenshot": {
    "name": "screenshot",
    "description": "Screenshot via CDP",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "selector": {
          "type": "string"
        },
        "xpath": {
          "type": "string"
        },
        "fullPage": {
          "type": "boolean",
          "default": false
        },
        "format": {
          "type": "string",
          "enum": [
            "png",
            "jpeg"
          ],
          "default": "png"
        },
        "quality": {
          "type": "integer",
          "default": 90
        },
        "clip": {
          "type": "object",
          "properties": {
            "x": {
              "type": "number"
            },
            "y": {
              "type": "number"
            },
            "width": {
              "type": "number"
            },
            "height": {
              "type": "number"
            },
            "scale": {
              "type": "number"
            }
          }
        },
        "omitBackground": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "pdf": {
    "name": "pdf",
    "description": "Generate PDF via CDP",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "format": {
          "type": "string",
          "enum": [
            "A4",
            "Letter",
            "Legal"
          ],
          "default": "A4"
        },
        "printBackground": {
          "type": "boolean",
          "default": true
        },
        "landscape": {
          "type": "boolean",
          "default": false
        },
        "margin": {
          "type": "object",
          "properties": {
            "top": {
              "type": "string"
            },
            "bottom": {
              "type": "string"
            },
            "left": {
              "type": "string"
            },
            "right": {
              "type": "string"
            }
          }
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "dom_snapshot": {
    "name": "dom_snapshot",
    "description": "Full DOM snapshot via CDP",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "includeStyles": {
          "type": "boolean",
          "default": false
        },
        "includePaintOrder": {
          "type": "boolean",
          "default": false
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "get_html": {
    "name": "get_html",
    "description": "Get page HTML",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "get_text": {
    "name": "get_text",
    "description": "Get page text content",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "persona_set": {
    "name": "persona_set",
    "description": "Configure human behavior persona",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "persona": {
          "type": "object"
        },
        "preset": {
          "type": "string",
          "enum": [
            "careful",
            "normal",
            "fast",
            "elderly",
            "power_user",
            "mobile"
          ]
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "persona_get": {
    "name": "persona_get",
    "description": "Get current persona configuration",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        }
      },
      "required": [
        "sessionId"
      ]
    }
  },
  "persona_list_modes": {
    "name": "persona_list_modes",
    "description": "List available behavior presets",
    "inputSchema": {
      "type": "object",
      "properties": {}
    }
  },
  "persona_list_templates": {
    "name": "persona_list_templates",
    "description": "List available persona templates",
    "inputSchema": {
      "type": "object",
      "properties": {}
    }
  },
  "persona_get_template": {
    "name": "persona_get_template",
    "description": "Get persona template by name",
    "inputSchema": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string"
        }
      },
      "required": [
        "name"
      ]
    }
  },
  "persona_validate": {
    "name": "persona_validate",
    "description": "Validate persona configuration",
    "inputSchema": {
      "type": "object",
      "properties": {
        "persona": {
          "type": "object"
        }
      },
      "required": [
        "persona"
      ]
    }
  },
  "persona_create": {
    "name": "persona_create",
    "description": "Create persona from template",
    "inputSchema": {
      "type": "object",
      "properties": {
        "template": {
          "type": "string"
        },
        "overrides": {
          "type": "object"
        }
      },
      "required": [
        "template"
      ]
    }
  }
};

async function handleRequest(request) {
  const { method, params } = request;
  try {
    switch (method) {
      case 'initialize': {
        return { protocolVersion: '2024-11-05', capabilities: { tools: {} }, serverInfo: { name: 'agent_browser', version: '1.0.0' } };
      }
      case 'tools/list': {
        return { tools: Object.values(TOOL_SCHEMAS) };
      }
      case 'tools/call': {
        const { name, arguments: args } = params;
        const handler = TOOLS[name];
        if (!handler) throw new Error('Unknown tool: ' + name);
        if (args.sessionId && !activeBrowsers.has(args.sessionId)) {
          await initializeBrowser(args.sessionId);
        }
        const result = await handler(args, {});
        return { content: [{ type: 'text', text: JSON.stringify(result, null, 2) }] };
      }
      case 'ping': { return { pong: true }; }
      default: throw new Error('Unknown method: ' + method);
    }
  } catch (error) {
    console.error('[MCP] Request error:', error.message);
    return { error: { code: -32603, message: error.message } };
  }
}

function startStdioServer() {
  console.error('[agent_browser] Starting MCP server on stdio...');

  // Set up notification callback for stdio transport
  notificationManager.on('notification', ({ sessionId, method, params }) => {
    // Send notification as JSON-RPC notification (no id)
    process.stdout.write(JSON.stringify({
      jsonrpc: '2.0',
      method: method || 'notifications/cdp_event',
      params: { sessionId, ...params }
    }) + '\n');
  });

  process.stdin.on('data', async (data) => {
    try {
      const lines = data.toString().trim().split('\n');
      for (const line of lines) {
        if (!line.trim()) continue;
        const request = JSON.parse(line);
        const response = await handleRequest(request);
        process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id: request.id, ...response }) + '\n');
      }
    } catch (e) { console.error('[agent_browser] Stdin error:', e.message); }
  });
  process.on('SIGINT', async () => { console.error('[agent_browser] Shutting down...'); for (const [sessionId] of activeBrowsers) { await closeBrowser(sessionId); } process.exit(0); });
  process.on('SIGTERM', async () => { console.error('[agent_browser] Shutting down...'); for (const [sessionId] of activeBrowsers) { await closeBrowser(sessionId); } process.exit(0); });
}

function startHttpServer(port = 3456) {
  const server = http.createServer(async (req, res) => {
    if (req.method === 'POST' && req.url === '/mcp') {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', async () => {
        try {
          const request = JSON.parse(body);
          const response = await handleRequest(request);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ jsonrpc: '2.0', id: request.id, ...response }));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ jsonrpc: '2.0', error: { code: -32700, message: 'Parse error' } }));
        }
      });
    } else if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ok', server: 'agent_browser', version: '1.0.0' }));
    } else { res.writeHead(404); res.end('Not found'); }
  });
  server.listen(port, () => console.error('[agent_browser] HTTP server listening on port ' + port));
}

if (require.main === module) {
  if (process.env.MCP_HTTP_PORT) startHttpServer(parseInt(process.env.MCP_HTTP_PORT));
  else startStdioServer();
}

module.exports = { handleRequest, TOOLS, TOOL_SCHEMAS, startStdioServer, startHttpServer, notificationManager, getNotificationManager };
