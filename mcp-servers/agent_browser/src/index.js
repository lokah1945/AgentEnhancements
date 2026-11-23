/**
 * agent_browser MCP Server - CDP browser automation over MCP (JSON-RPC 2.0).
 *
 * Transports:
 *   - stdio (default): newline-delimited JSON-RPC frames on stdin/stdout.
 *     stdout carries protocol frames only; every diagnostic goes to stderr.
 *   - HTTP (MCP_HTTP_PORT set): POST /mcp with application/json bodies,
 *     bound to 127.0.0.1 by default (see startHttpServer).
 */

if (require.main === module) {
  // Keep the stdio protocol channel clean, including for anything a
  // dependency logs while it loads.
  for (const level of ['log', 'info', 'debug']) {
    console[level] = (...args) => console.error(...args);
  }
}

const crypto = require('crypto');
const http = require('http');
const {
  initializeBrowser,
  closeBrowser,
  activeBrowsers
} = require('./cdp-router-wrapper');
const { notificationManager, getNotificationManager } = require('./notifications');
const {
  RPC_ERRORS,
  RpcError,
  isPlainObject,
  isValidId,
  errorResponse,
  validateArguments,
  createLineDecoder,
  createSerialQueue
} = require('./jsonrpc');
const { version: SERVER_VERSION } = require('../package.json');

/** Protocol revisions this server can speak, newest first. */
const SUPPORTED_PROTOCOL_VERSIONS = ['2025-06-18', '2025-03-26', '2024-11-05'];

/**
 * Subscribe a callback to every server-to-client notification.
 */
function setNotificationCallback(callback) {
  notificationManager.on('notification', callback);
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
  session_close: sessionTools.sessionClose,

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

/**
 * Tools that operate on a live page. Calling one for a session whose browser
 * is not running launches it first. Session lifecycle, capture bookkeeping and
 * persona tools never launch Chromium.
 */
const BROWSER_TOOLS = new Set([
  'navigate', 'go_back', 'go_forward', 'reload', 'get_current_url',
  'tab_new', 'tab_switch', 'tab_close', 'tab_list', 'tab_get',
  'click', 'type', 'hover', 'scroll', 'drag_drop', 'key_press',
  'cdp_send', 'cdp_evaluate', 'cdp_subscribe', 'cdp_unsubscribe',
  'cdp_network_capture', 'cdp_console_capture', 'cdp_metrics',
  'extract', 'get_attributes', 'get_page_content',
  'screenshot', 'pdf', 'dom_snapshot', 'get_html', 'get_text'
]);

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
          "description": "Recorded as session metadata only; the Playwright-bundled Chromium is launched",
          "enum": [
            "chrome",
            "edge",
            "chromium"
          ],
          "default": "chrome"
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
  "session_close": {
    "name": "session_close",
    "description": "Close the session's browser (profile and metadata are kept)",
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
    "description": "Delete session and its profile; an open browser for the session is closed first",
    "inputSchema": {
      "type": "object",
      "properties": {
        "sessionId": {
          "type": "string"
        },
        "force": {
          "type": "boolean",
          "description": "Also delete a session that is still marked active by another process"
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
          "type": "object",
          "description": "Extra HTTP headers; they stay set for later requests of this tab"
        },
        "timeout": {
          "type": "number",
          "description": "Milliseconds to wait for waitUntil (default 30000)"
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
    "description": "Close tab (by tabIndex or tabId)",
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
          "description": "'frame' targets the tab whose main frame is frameId",
          "enum": [
            "page",
            "frame"
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
          "description": "'frame' targets the tab whose main frame is frameId",
          "enum": [
            "page",
            "frame"
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
    "description": "Build a human behavior persona; it is returned, not stored, so pass it as the persona argument of interaction tools",
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
    "description": "Get the default persona configuration (personas are not stored per session)",
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

/** True when a handler's return value describes a failure. */
function isToolFailure(result) {
  return isPlainObject(result) && (result.success === false || isPlainObject(result.error));
}

async function callTool(params) {
  if (!isPlainObject(params)) {
    throw new RpcError(RPC_ERRORS.INVALID_PARAMS, 'tools/call requires a params object');
  }
  const { name } = params;
  if (typeof name !== 'string' || !Object.prototype.hasOwnProperty.call(TOOLS, name)) {
    throw new RpcError(RPC_ERRORS.INVALID_PARAMS, `Unknown tool: ${name}`);
  }
  const args = params.arguments === undefined || params.arguments === null ? {} : params.arguments;
  const problem = validateArguments(TOOL_SCHEMAS[name].inputSchema, args);
  if (problem) {
    throw new RpcError(RPC_ERRORS.INVALID_PARAMS, `Invalid arguments for ${name}: ${problem}`);
  }

  let result;
  try {
    if (BROWSER_TOOLS.has(name) && !activeBrowsers.has(args.sessionId)) {
      await initializeBrowser(args.sessionId);
    }
    result = await TOOLS[name](args, {});
  } catch (error) {
    // MCP: failures inside a tool are results flagged isError, so the model sees them.
    console.error(`[agent_browser] Tool ${name} failed:`, error && error.message);
    return {
      content: [{ type: 'text', text: (error && error.message) || String(error) }],
      isError: true
    };
  }
  const text = JSON.stringify(result === undefined ? null : result, null, 2);
  const response = { content: [{ type: 'text', text }] };
  if (isToolFailure(result)) response.isError = true;
  return response;
}

/**
 * Dispatch one request. Returns `{ result }` on success or `{ error }` with a
 * JSON-RPC error object; never throws.
 */
async function handleRequest(request) {
  const { method, params } = request || {};
  try {
    switch (method) {
      case 'initialize': {
        const requested = isPlainObject(params) ? params.protocolVersion : undefined;
        const protocolVersion = SUPPORTED_PROTOCOL_VERSIONS.includes(requested)
          ? requested
          : SUPPORTED_PROTOCOL_VERSIONS[0];
        return {
          result: {
            protocolVersion,
            capabilities: { tools: { listChanged: false } },
            serverInfo: { name: 'agent_browser', version: SERVER_VERSION }
          }
        };
      }
      case 'ping':
        return { result: {} };
      case 'tools/list':
        return { result: { tools: Object.values(TOOL_SCHEMAS) } };
      case 'tools/call':
        return { result: await callTool(params) };
      default:
        throw new RpcError(RPC_ERRORS.METHOD_NOT_FOUND, `Method not found: ${method}`);
    }
  } catch (error) {
    if (error instanceof RpcError) return { error: error.toJSON() };
    console.error('[MCP] Request error:', error && error.stack);
    return { error: { code: RPC_ERRORS.INTERNAL_ERROR, message: (error && error.message) || 'Internal error' } };
  }
}

/**
 * Handle one decoded JSON-RPC message (object or batch array).
 * Returns the response to send, or null when nothing must be sent
 * (notifications, client responses, all-notification batches).
 */
async function processMessage(message) {
  if (Array.isArray(message)) {
    if (message.length === 0) {
      return errorResponse(null, RPC_ERRORS.INVALID_REQUEST, 'Invalid Request: empty batch');
    }
    const responses = [];
    for (const item of message) {
      const response = await processMessage(item);
      if (response) responses.push(response);
    }
    return responses.length ? responses : null;
  }
  if (!isPlainObject(message)) {
    return errorResponse(null, RPC_ERRORS.INVALID_REQUEST, 'Invalid Request');
  }
  const hasId = Object.prototype.hasOwnProperty.call(message, 'id') && message.id !== undefined;
  if (typeof message.method !== 'string') {
    // A response to a server-initiated request: nothing to answer.
    if (hasId && ('result' in message || 'error' in message)) return null;
    return errorResponse(hasId && isValidId(message.id) ? message.id : null,
      RPC_ERRORS.INVALID_REQUEST, 'Invalid Request: method must be a string');
  }
  if (!hasId) {
    // Notification: never answered. notifications/* need no action here.
    if (!message.method.startsWith('notifications/')) await handleRequest(message);
    return null;
  }
  if (!isValidId(message.id)) {
    return errorResponse(null, RPC_ERRORS.INVALID_REQUEST, 'Invalid Request: id must be a string or number');
  }
  if (message.jsonrpc !== '2.0') {
    return errorResponse(message.id, RPC_ERRORS.INVALID_REQUEST, 'Invalid Request: jsonrpc must be "2.0"');
  }
  const outcome = await handleRequest(message);
  return { jsonrpc: '2.0', id: message.id, ...outcome };
}

// Browser state is shared by every transport, so requests run one at a time.
const enqueue = createSerialQueue();

async function closeAllBrowsers() {
  for (const sessionId of [...activeBrowsers.keys()]) {
    try {
      await closeBrowser(sessionId);
    } catch (e) {
      console.error(`[agent_browser] Failed to close ${sessionId}:`, e.message);
    }
  }
}

function writeFrame(message) {
  process.stdout.write(JSON.stringify(message) + '\n');
}

function startStdioServer() {
  console.error('[agent_browser] Starting MCP server on stdio...');

  notificationManager.on('notification', ({ sessionId, method, params }) => {
    writeFrame({
      jsonrpc: '2.0',
      method: method || 'notifications/cdp_event',
      params: { sessionId, ...params }
    });
  });

  const decoder = createLineDecoder((line) => {
    if (!line.trim()) return;
    let message;
    try {
      message = JSON.parse(line);
    } catch (e) {
      writeFrame(errorResponse(null, RPC_ERRORS.PARSE_ERROR, 'Parse error'));
      return;
    }
    enqueue(async () => {
      const response = await processMessage(message);
      if (response) writeFrame(response);
    }).catch((e) => console.error('[agent_browser] Request failed:', e && e.stack));
  }, {
    maxBytes: Number(process.env.AGENT_BROWSER_MAX_MESSAGE_BYTES) || 64 * 1024 * 1024,
    onOverflow: () => writeFrame(errorResponse(null, RPC_ERRORS.INVALID_REQUEST, 'Message too large'))
  });

  let shuttingDown = false;
  async function shutdown(code) {
    if (shuttingDown) return;
    shuttingDown = true;
    console.error('[agent_browser] Shutting down...');
    await closeAllBrowsers();
    process.exit(code);
  }

  process.stdin.on('data', (chunk) => decoder.push(chunk));
  process.stdin.on('end', () => {
    decoder.end();
    // Answer everything already received, then release the browsers.
    enqueue(() => shutdown(0));
  });
  process.on('SIGINT', () => shutdown(0));
  process.on('SIGTERM', () => shutdown(0));
}

const LOOPBACK_HOSTS = new Set(['127.0.0.1', '::1', 'localhost']);

function isLoopbackHost(host) {
  return LOOPBACK_HOSTS.has(String(host).replace(/^\[|\]$/g, '').toLowerCase());
}

/** Host header without the port, lower-cased ("[::1]:80" -> "::1"). */
function hostnameOf(hostHeader) {
  const value = String(hostHeader || '').trim().toLowerCase();
  if (value.startsWith('[')) return value.slice(1, value.indexOf(']'));
  return value.replace(/:\d+$/, '');
}

function isAllowedOrigin(origin, allowedOrigins) {
  if (allowedOrigins.includes(origin)) return true;
  try {
    const url = new URL(origin);
    return (url.protocol === 'http:' || url.protocol === 'https:') && isLoopbackHost(url.hostname);
  } catch (e) {
    return false;
  }
}

function tokensMatch(presented, expected) {
  // Hash both sides so timingSafeEqual always compares equal-length buffers.
  const a = crypto.createHash('sha256').update(String(presented)).digest();
  const b = crypto.createHash('sha256').update(String(expected)).digest();
  return crypto.timingSafeEqual(a, b);
}

/**
 * Start the HTTP transport. Options (environment fallbacks in brackets):
 *   port           [MCP_HTTP_PORT]                       default 3456
 *   host           [MCP_HTTP_HOST]                       default 127.0.0.1
 *   token          [AGENT_BROWSER_HTTP_TOKEN]            optional on loopback, required otherwise
 *   maxBodyBytes   [AGENT_BROWSER_HTTP_MAX_BODY_BYTES]   default 1 MiB
 *   allowedOrigins [AGENT_BROWSER_HTTP_ALLOWED_ORIGINS]  comma list, in addition to loopback origins
 * Resolves with the listening http.Server.
 */
function startHttpServer(options = {}) {
  if (typeof options === 'number') options = { port: options };
  const env = process.env;
  const port = options.port !== undefined ? options.port : Number(env.MCP_HTTP_PORT || 3456);
  const host = options.host || env.MCP_HTTP_HOST || '127.0.0.1';
  const token = options.token !== undefined ? options.token : (env.AGENT_BROWSER_HTTP_TOKEN || '');
  const maxBodyBytes = options.maxBodyBytes || Number(env.AGENT_BROWSER_HTTP_MAX_BODY_BYTES) || 1024 * 1024;
  const allowedOrigins = options.allowedOrigins ||
    String(env.AGENT_BROWSER_HTTP_ALLOWED_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const loopback = isLoopbackHost(host);

  if (!loopback && !token) {
    return Promise.reject(new Error(
      `Refusing to bind the HTTP transport to non-loopback host ${host} without AGENT_BROWSER_HTTP_TOKEN`));
  }

  function send(res, status, body, headers = {}) {
    const payload = body === undefined ? '' : JSON.stringify(body);
    res.writeHead(status, {
      ...(payload ? { 'Content-Type': 'application/json' } : {}),
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      ...headers
    });
    res.end(payload);
  }

  const server = http.createServer((req, res) => {
    // DNS rebinding: a loopback-bound server only answers loopback Host names.
    if (loopback && !isLoopbackHost(hostnameOf(req.headers.host))) {
      return send(res, 403, { error: 'Forbidden host' });
    }
    if (req.headers.origin !== undefined && !isAllowedOrigin(req.headers.origin, allowedOrigins)) {
      return send(res, 403, { error: 'Forbidden origin' });
    }

    const url = (req.url || '').split('?')[0];
    if (url === '/health') {
      if (req.method !== 'GET') return send(res, 405, { error: 'Method not allowed' }, { Allow: 'GET' });
      return send(res, 200, { status: 'ok', server: 'agent_browser', version: SERVER_VERSION });
    }
    if (url !== '/mcp') return send(res, 404, { error: 'Not found' });
    if (req.method !== 'POST') return send(res, 405, { error: 'Method not allowed' }, { Allow: 'POST' });

    if (token) {
      const match = /^Bearer\s+(.+)$/i.exec(req.headers.authorization || '');
      if (!match || !tokensMatch(match[1].trim(), token)) {
        return send(res, 401, { error: 'Unauthorized' }, { 'WWW-Authenticate': 'Bearer' });
      }
    }
    const contentType = String(req.headers['content-type'] || '').split(';')[0].trim().toLowerCase();
    if (contentType !== 'application/json') {
      return send(res, 415, { error: 'Content-Type must be application/json' });
    }
    const declared = Number(req.headers['content-length']);
    if (Number.isFinite(declared) && declared > maxBodyBytes) {
      return send(res, 413, { error: 'Payload too large' }, { Connection: 'close' });
    }

    const chunks = [];
    let size = 0;
    let rejected = false;
    req.on('data', (chunk) => {
      if (rejected) return;
      size += chunk.length;
      if (size > maxBodyBytes) {
        rejected = true;
        res.on('finish', () => req.destroy());
        send(res, 413, { error: 'Payload too large' }, { Connection: 'close' });
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', async () => {
      if (rejected) return;
      let message;
      try {
        message = JSON.parse(Buffer.concat(chunks).toString('utf8'));
      } catch (e) {
        return send(res, 400, errorResponse(null, RPC_ERRORS.PARSE_ERROR, 'Parse error'));
      }
      try {
        const response = await enqueue(() => processMessage(message));
        if (!response) return send(res, 202);
        return send(res, 200, response);
      } catch (e) {
        console.error('[agent_browser] HTTP request failed:', e && e.stack);
        return send(res, 500, errorResponse(null, RPC_ERRORS.INTERNAL_ERROR, 'Internal error'));
      }
    });
  });

  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => {
      server.removeListener('error', reject);
      const address = server.address();
      console.error(`[agent_browser] HTTP server listening on ${address.address}:${address.port}` +
        (token ? ' (bearer token required)' : ''));
      resolve(server);
    });
  });
}

if (require.main === module) {
  if (process.env.MCP_HTTP_PORT) {
    startHttpServer().then((server) => {
      const stop = async () => {
        server.close();
        await closeAllBrowsers();
        process.exit(0);
      };
      process.on('SIGINT', stop);
      process.on('SIGTERM', stop);
    }, (error) => {
      console.error('[agent_browser]', error.message);
      process.exit(1);
    });
  } else {
    startStdioServer();
  }
}

module.exports = {
  handleRequest,
  processMessage,
  TOOLS,
  TOOL_SCHEMAS,
  BROWSER_TOOLS,
  SUPPORTED_PROTOCOL_VERSIONS,
  startStdioServer,
  startHttpServer,
  setNotificationCallback,
  notificationManager,
  getNotificationManager
};
