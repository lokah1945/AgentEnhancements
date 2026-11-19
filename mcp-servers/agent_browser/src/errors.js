/**
 * errors.js - Standardized error handling for agent_browser MCP server
 *
 * Provides consistent error format matching MCP specification:
 * { error: { code: number, message: string, data?: any } }
 *
 * Error codes (MCP standard + custom):
 * -32700: Parse error
 * -32600: Invalid request
 * -32601: Method not found
 * -32602: Invalid params
 * -32603: Internal error
 * -32000 to -32099: Server-defined errors
 */

// Custom error codes for agent_browser
const ERROR_CODES = {
  // Session errors (-32000 to -32009)
  SESSION_NOT_FOUND: -32000,
  SESSION_ALREADY_EXISTS: -32001,
  SESSION_NOT_ACTIVE: -32002,
  SESSION_INIT_FAILED: -32003,
  SESSION_INIT_IN_PROGRESS: -32004,

  // Browser errors (-32010 to -32019)
  BROWSER_LAUNCH_FAILED: -32010,
  BROWSER_CRASHED: -32011,
  BROWSER_ALREADY_CLOSED: -32012,

  // Page/Tab errors (-32020 to -32029)
  PAGE_NOT_FOUND: -32020,
  PAGE_NAVIGATION_FAILED: -32021,
  PAGE_LOAD_TIMEOUT: -32022,
  TAB_INDEX_OUT_OF_RANGE: -32023,

  // Element errors (-32030 to -32039)
  ELEMENT_NOT_FOUND: -32030,
  ELEMENT_NOT_INTERACTABLE: -32031,
  ELEMENT_STALE: -32032,

  // CDP errors (-32040 to -32049)
  CDP_SESSION_FAILED: -32040,
  CDP_COMMAND_FAILED: -32041,
  CDP_DOMAIN_NOT_AVAILABLE: -32042,
  CDP_SUBSCRIPTION_NOT_FOUND: -32043,

  // Capture errors (-32050 to -32059)
  CAPTURE_NOT_FOUND: -32050,
  CAPTURE_ALREADY_STOPPED: -32051,

  // Profile/Storage errors (-32060 to -32069)
  PROFILE_NOT_FOUND: -32060,
  PROFILE_CORRUPTED: -32061,
  STORAGE_EXTRACTION_FAILED: -32062,

  // Persona/Behavior errors (-32070 to -32079)
  PERSONA_INVALID: -32070,
  PERSONA_TEMPLATE_NOT_FOUND: -32071,

  // Validation errors (-32080 to -32089)
  VALIDATION_FAILED: -32080,
  INVALID_ARGUMENTS: -32081,

  // Network/Proxy errors (-32090 to -32099)
  NETWORK_ERROR: -32090,
  PROXY_ERROR: -32091
};

/**
 * Create standardized MCP error object
 * @param {number} code - Error code
 * @param {string} message - Error message
 * @param {any} data - Optional additional data
 * @returns {object} MCP error object
 */
function createMCPError(code, message, data = undefined) {
  const error = { code, message };
  if (data !== undefined) {
    error.data = data;
  }
  return { error };
}

/**
 * Create error for session not found
 */
function sessionNotFound(sessionId) {
  return createMCPError(
    ERROR_CODES.SESSION_NOT_FOUND,
    `Session not found: ${sessionId}`,
    { sessionId }
  );
}

/**
 * Create error for element not found
 */
function elementNotFound(selector, xpath) {
  const target = selector || xpath;
  return createMCPError(
    ERROR_CODES.ELEMENT_NOT_FOUND,
    `Element not found: ${target}`,
    { selector, xpath }
  );
}

/**
 * Create error for page not found
 */
function pageNotFound(pageId) {
  return createMCPError(
    ERROR_CODES.PAGE_NOT_FOUND,
    `Page not found: ${pageId}`,
    { pageId }
  );
}

/**
 * Create error for tab index out of range
 */
function tabIndexOutOfRange(tabIndex, maxIndex) {
  return createMCPError(
    ERROR_CODES.TAB_INDEX_OUT_OF_RANGE,
    `Tab index ${tabIndex} out of range (0-${maxIndex})`,
    { tabIndex, maxIndex }
  );
}

/**
 * Create error for CDP command failed
 */
function cdpCommandFailed(domain, method, originalError) {
  return createMCPError(
    ERROR_CODES.CDP_COMMAND_FAILED,
    `CDP command failed: ${domain}.${method} - ${originalError.message}`,
    { domain, method, originalError: originalError.message }
  );
}

/**
 * Create error for capture not found
 */
function captureNotFound(captureId) {
  return createMCPError(
    ERROR_CODES.CAPTURE_NOT_FOUND,
    `Capture not found: ${captureId}`,
    { captureId }
  );
}

/**
 * Create error for subscription not found
 */
function subscriptionNotFound(subscriptionId) {
  return createMCPError(
    ERROR_CODES.CDP_SUBSCRIPTION_NOT_FOUND,
    `Subscription not found: ${subscriptionId}`,
    { subscriptionId }
  );
}

/**
 * Create error for validation failed
 */
function validationFailed(message, details) {
  return createMCPError(
    ERROR_CODES.VALIDATION_FAILED,
    message,
    details
  );
}

/**
 * Create error for invalid arguments
 */
function invalidArguments(message, args) {
  return createMCPError(
    ERROR_CODES.INVALID_ARGUMENTS,
    message,
    { args }
  );
}

/**
 * Create error for browser launch failed
 */
function browserLaunchFailed(originalError) {
  return createMCPError(
    ERROR_CODES.BROWSER_LAUNCH_FAILED,
    `Browser launch failed: ${originalError.message}`,
    { originalError: originalError.message, stack: originalError.stack }
  );
}

/**
 * Create error for navigation failed
 */
function navigationFailed(url, originalError) {
  return createMCPError(
    ERROR_CODES.PAGE_NAVIGATION_FAILED,
    `Navigation failed for ${url}: ${originalError.message}`,
    { url, originalError: originalError.message }
  );
}

/**
 * Create error for profile not found
 */
function profileNotFound(profilePath) {
  return createMCPError(
    ERROR_CODES.PROFILE_NOT_FOUND,
    `Profile not found: ${profilePath}`,
    { profilePath }
  );
}

/**
 * Create error for persona template not found
 */
function personaTemplateNotFound(template) {
  return createMCPError(
    ERROR_CODES.PERSONA_TEMPLATE_NOT_FOUND,
    `Persona template not found: ${template}`,
    { template }
  );
}

/**
 * Wrap async function with standardized error handling
 * @param {Function} fn - Async function to wrap
 * @returns {Function} Wrapped function that returns { success: true, data } or { error: {...} }
 */
function withErrorHandling(fn) {
  return async (...args) => {
    try {
      const result = await fn(...args);
      // If result already has error property, return as-is
      if (result && result.error) {
        return result;
      }
      return { success: true, ...result };
    } catch (error) {
      console.error('[ErrorHandler]', error.message);
      return createMCPError(
        ERROR_CODES.INTERNAL_ERROR || -32603,
        error.message,
        { stack: error.stack }
      );
    }
  };
}

/**
 * Wrap sync function with standardized error handling
 * @param {Function} fn - Sync function to wrap
 * @returns {Function} Wrapped function
 */
function withErrorHandlingSync(fn) {
  return (...args) => {
    try {
      const result = fn(...args);
      if (result && result.error) {
        return result;
      }
      return { success: true, ...result };
    } catch (error) {
      console.error('[ErrorHandler]', error.message);
      return createMCPError(
        ERROR_CODES.INTERNAL_ERROR || -32603,
        error.message,
        { stack: error.stack }
      );
    }
  };
}

module.exports = {
  ERROR_CODES,
  createMCPError,
  sessionNotFound,
  elementNotFound,
  pageNotFound,
  tabIndexOutOfRange,
  cdpCommandFailed,
  captureNotFound,
  subscriptionNotFound,
  validationFailed,
  invalidArguments,
  browserLaunchFailed,
  navigationFailed,
  profileNotFound,
  personaTemplateNotFound,
  withErrorHandling,
  withErrorHandlingSync
};