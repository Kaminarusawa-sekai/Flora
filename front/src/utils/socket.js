class WebSocketClient {
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.socket = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 1000;
    this.connected = false;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(this.url, this.options.protocols);

        this.socket.onopen = (event) => {
          this.connected = true;
          this.reconnectAttempts = 0;
          this.emit('open', event);
          resolve(event);
        };

        this.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.emit('message', data);
          } catch (error) {
            this.emit('message', event.data);
          }
        };

        this.socket.onclose = (event) => {
          this.connected = false;
          this.emit('close', event);
          this.handleReconnect();
        };

        this.socket.onerror = (error) => {
          this.emit('error', error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(error => {
          console.error(`WebSocket reconnect attempt ${this.reconnectAttempts} failed:`, error);
        });
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)); // 指数退避
    } else {
      this.emit('max-reconnect-attempts', this.maxReconnectAttempts);
    }
  }

  send(data) {
    if (this.connected && this.socket.readyState === WebSocket.OPEN) {
      const message = typeof data === 'object' ? JSON.stringify(data) : data;
      this.socket.send(message);
      return true;
    }
    return false;
  }

  on(eventType, callback) {
    if (!this.listeners[eventType]) {
      this.listeners[eventType] = [];
    }
    this.listeners[eventType].push(callback);
    return this;
  }

  off(eventType, callback) {
    if (this.listeners[eventType]) {
      this.listeners[eventType] = this.listeners[eventType].filter(cb => cb !== callback);
    }
    return this;
  }

  emit(eventType, data) {
    if (this.listeners[eventType]) {
      this.listeners[eventType].forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error(`Error in ${eventType} listener:`, error);
        }
      });
    }
  }

  close(code, reason) {
    if (this.socket) {
      this.socket.close(code, reason);
      this.socket = null;
      this.connected = false;
      this.emit('close', { code, reason });
    }
  }

  getReadyState() {
    return this.socket ? this.socket.readyState : WebSocket.CLOSED;
  }

  isConnected() {
    return this.connected;
  }
}

/**
 * 创建 WebSocket 客户端实例
 * @param {string} url - WebSocket 服务器 URL
 * @param {Object} options - 配置选项
 * @returns {WebSocketClient} WebSocket 客户端实例
 */
export function createWebSocketClient(url, options = {}) {
  return new WebSocketClient(url, options);
}

/**
 * 生成 Trace WebSocket URL
 * @param {string} traceId - Trace ID
 * @returns {string} 完整的 WebSocket URL
 */
export function getTraceWebSocketUrl(traceId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/traces/ws/${traceId}`;
}

/**
 * 生成 Trace WebSocket URL（相对路径）
 * @param {string} traceId - Trace ID
 * @returns {string} 相对 WebSocket URL
 */
export function getTraceWebSocketRelativeUrl(traceId) {
  return `/traces/ws/${traceId}`;
}
