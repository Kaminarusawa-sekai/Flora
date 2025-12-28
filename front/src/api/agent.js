// API 基础 URL
const API_BASE_URL = 'http://localhost:8000';

/**
 * Agent API 服务，用于处理与Agent相关的WebSocket连接
 */
class AgentAPI {
  /**
   * 创建Agent树WebSocket连接
   * @param {string} agentId - Agent ID
   * @param {Object} callbacks - 回调函数对象
   * @param {Function} callbacks.onOpen - 连接打开时的回调
   * @param {Function} callbacks.onMessage - 接收消息时的回调
   * @param {Function} callbacks.onError - 发生错误时的回调
   * @param {Function} callbacks.onClose - 连接关闭时的回调
   * @returns {WebSocket} WebSocket实例
   */
  static createAgentTreeWebSocket(agentId, callbacks = {}) {
    const { onOpen, onMessage, onError, onClose } = callbacks;
    
    // 构建WebSocket URL
    const wsUrl = API_BASE_URL.replace('http', 'ws') + `/ws/agent/${agentId}`;
    
    // 创建WebSocket连接
    const ws = new WebSocket(wsUrl);
    
    // 设置事件处理程序
    ws.onopen = (event) => {
      console.log(`WebSocket connected to agent ${agentId}`);
      if (onOpen) onOpen(event);
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
        if (onError) onError(error);
      }
    };
    
    ws.onerror = (error) => {
      console.error(`WebSocket error for agent ${agentId}:`, error);
      if (onError) onError(error);
    };
    
    ws.onclose = (event) => {
      console.log(`WebSocket disconnected from agent ${agentId}`, event.code, event.reason);
      if (onClose) onClose(event);
    };
    
    return ws;
  }
  
  /**
   * 发送refresh指令到WebSocket连接
   * @param {WebSocket} ws - WebSocket实例
   */
  static refreshAgentTree(ws) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send('refresh');
    } else {
      console.error('WebSocket is not open, cannot send refresh command');
    }
  }
  
  /**
   * 关闭Agent树WebSocket连接
   * @param {WebSocket} ws - WebSocket实例
   */
  static closeAgentTreeWebSocket(ws) {
    if (ws) {
      ws.close();
    }
  }
}

export default AgentAPI;