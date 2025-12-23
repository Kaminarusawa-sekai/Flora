class SSEClient {
  constructor(url, options = {}) {
    this.url = url;
    this.options = options;
    this.eventSource = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 5;
    this.reconnectDelay = options.reconnectDelay || 1000;
    this.connected = false;
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        this.eventSource = new EventSource(this.url, this.options);

        this.eventSource.onopen = (event) => {
          this.connected = true;
          this.reconnectAttempts = 0;
          this.emit('open', event);
          resolve(event);
        };

        this.eventSource.onmessage = (event) => {
          this.emit('message', event.data);
        };

        this.eventSource.onerror = (error) => {
          this.connected = false;
          this.emit('error', error);
          
          if (this.eventSource.readyState === EventSource.CLOSED) {
            this.handleReconnect();
          }
        };

        // 处理自定义事件
        if (this.options.events) {
          this.options.events.forEach(eventType => {
            this.eventSource.addEventListener(eventType, (event) => {
              if (event.data) {
                try {
                  this.emit(eventType, JSON.parse(event.data));
                } catch (error) {
                  console.error(`Failed to parse SSE event data for ${eventType}:`, error);
                }
              }
            });
          });
        }
      } catch (error) {
        this.connected = false;
        this.emit('error', error);
        this.handleReconnect();
        reject(error);
      }
    });
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        this.connect().catch(error => {
          console.error(`Reconnect attempt ${this.reconnectAttempts} failed:`, error);
        });
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)); // 指数退避
    } else {
      this.emit('max-reconnect-attempts', this.maxReconnectAttempts);
    }
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

  close() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.connected = false;
      this.emit('close');
    }
  }

  getReadyState() {
    return this.eventSource ? this.eventSource.readyState : EventSource.CLOSED;
  }

  isConnected() {
    return this.connected;
  }
}

/**
 * 创建 SSE 客户端实例
 * @param {string} url - SSE 服务器 URL
 * @param {Object} options - 配置选项
 * @returns {SSEClient} SSE 客户端实例
 */
export function createSSEClient(url, options = {}) {
  return new SSEClient(url, options);
}

/**
 * 生成对话事件流 URL
 * @param {string} sessionId - 会话 ID
 * @returns {string} 完整的 SSE URL
 */
export function getConversationStreamUrl(sessionId) {
  return ` http://localhost:8000/v1/conversations/${sessionId}/stream`;
}
