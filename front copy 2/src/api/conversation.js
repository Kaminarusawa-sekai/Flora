import { createSSEClient, getConversationStreamUrl } from '../utils/sse';

// API 基础 URL
const API_BASE_URL = 'http://localhost:8000';

/**
 * 会话 API 服务
 */
class ConversationAPI {
  /**
   * 获取用户所有活跃会话
   * @param {string} userId - 用户 ID
   * @returns {Promise<Array>} 会话列表
   */
  static async getUserSessions(userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/user/${userId}/sessions`);
      if (!response.ok) {
        throw new Error(`Failed to get user sessions: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching user sessions:', error);
      throw error;
    }
  }

  /**
   * 获取会话历史记录
   * @param {string} sessionId - 会话 ID
   * @param {Object} options - 查询选项
   * @param {number} options.limit - 限制返回数量
   * @param {number} options.offset - 偏移量
   * @returns {Promise<Array>} 历史记录列表
   */
  static async getSessionHistory(sessionId, options = { limit: 20, offset: 0 }) {
    try {
      const { limit, offset } = options;
      const response = await fetch(`${API_BASE_URL}/session/${sessionId}/history?limit=${limit}&offset=${offset}`);
      if (!response.ok) {
        throw new Error(`Failed to get session history: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching session history:', error);
      throw error;
    }
  }

  /**
   * 获取用户所有对话历史
   * @param {string} userId - 用户 ID
   * @param {Object} options - 查询选项
   * @param {number} options.limit - 限制返回数量
   * @param {number} options.offset - 偏移量
   * @returns {Promise<Array>} 历史记录列表
   */
  static async getUserHistory(userId, options = { limit: 20, offset: 0 }) {
    try {
      const { limit, offset } = options;
      const response = await fetch(`${API_BASE_URL}/user/${userId}/history?limit=${limit}&offset=${offset}`);
      if (!response.ok) {
        throw new Error(`Failed to get user history: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching user history:', error);
      throw error;
    }
  }

  /**
   * 获取会话信息
   * @param {string} sessionId - 会话 ID
   * @returns {Promise<Object>} 会话信息
   */
  static async getSessionInfo(sessionId) {
    try {
      const response = await fetch(`${API_BASE_URL}/session/${sessionId}`);
      if (!response.ok) {
        throw new Error(`Failed to get session info: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error fetching session info:', error);
      throw error;
    }
  }

  /**
   * 发送用户消息到会话
   * @param {string} sessionId - 会话 ID
   * @param {Object} message - 消息对象
   * @param {string} message.utterance - 消息内容
   * @param {number} message.timestamp - 时间戳
   * @param {Object} message.metadata - 元数据
   * @returns {Promise<Object>} 发送结果
   */
  static async sendMessage(sessionId, message) {
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(message)
      });
      if (!response.ok) {
        throw new Error(`Failed to send message: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }

  /**
   * 创建 SSE 连接以接收实时消息
   * @param {string} sessionId - 会话 ID
   * @param {Object} options - SSE 选项
   * @returns {Object} SSE 客户端实例
   */
  static createSessionStream(sessionId, options = {}) {
    const url = getConversationStreamUrl(sessionId);
    return createSSEClient(url, options);
  }

  /**
   * 绑定用户到会话
   * @param {string} sessionId - 会话 ID
   * @param {string} userId - 用户 ID
   * @returns {Promise<Object>} 绑定结果
   */
  static async bindUserToSession(sessionId, userId) {
    try {
      const response = await fetch(`${API_BASE_URL}/session/${sessionId}/bind-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_id: userId })
      });
      if (!response.ok) {
        throw new Error(`Failed to bind user to session: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error('Error binding user to session:', error);
      throw error;
    }
  }
}

export default ConversationAPI;
