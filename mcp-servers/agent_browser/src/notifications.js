/**
 * notifications.js - Server-to-client MCP notification fan-out.
 *
 * Lives in its own module so tool modules can require it without a circular
 * dependency on index.js. The stdio transport subscribes to 'notification'
 * events and writes them as JSON-RPC notifications (no id).
 */

const EventEmitter = require('events');

class NotificationManager extends EventEmitter {
  constructor() {
    super();
    this.notificationCallbacks = new Map(); // sessionId -> callback
  }

  /** Register a notification callback for a session. */
  registerSessionCallback(sessionId, callback) {
    this.notificationCallbacks.set(sessionId, callback);
  }

  /** Unregister a session's notification callback. */
  unregisterSessionCallback(sessionId) {
    this.notificationCallbacks.delete(sessionId);
  }

  /** Send a notification for one session (callback + global listeners). */
  sendNotification(sessionId, method, params) {
    const callback = this.notificationCallbacks.get(sessionId);
    if (callback) {
      try {
        callback({ method, params });
      } catch (e) {
        console.error('[NotificationManager] Callback error:', e.message);
      }
    }
    try {
      this.emit('notification', { sessionId, method, params });
    } catch (e) {
      console.error('[NotificationManager] Listener error:', e.message);
    }
  }

  /** Broadcast a notification to every registered session callback. */
  broadcastNotification(method, params) {
    for (const callback of this.notificationCallbacks.values()) {
      try {
        callback({ method, params });
      } catch (e) {
        console.error('[NotificationManager] Broadcast callback error:', e.message);
      }
    }
  }
}

const notificationManager = new NotificationManager();

function getNotificationManager() {
  return notificationManager;
}

module.exports = { NotificationManager, notificationManager, getNotificationManager };
