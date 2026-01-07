// API 基础 URL
const INTERACTION_API_BASE_URL = 'http://localhost:8000/v1';

/**
 * RAG API 服务
 */
class RAGAPI {
  /**
   * 获取文件列表
   * @returns {Promise<Array>} 文件列表
   */
  static async getFiles() {
    try {
      const response = await fetch(`${INTERACTION_API_BASE_URL}/rag/documents`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || response.statusText);
      }
      return data;
    } catch (error) {
      console.error('Error fetching files:', error);
      throw error;
    }
  }

  /**
   * 上传文件
   * @param {File} file - 要上传的文件
   * @returns {Promise<Object>} 上传结果
   */
  static async uploadFile(file) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await fetch(`${INTERACTION_API_BASE_URL}/rag/documents`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data?.error) {
        throw new Error(data?.error || data?.detail || response.statusText);
      }
      return data;
    } catch (error) {
      console.error('Error uploading file:', error);
      throw error;
    }
  }

  /**
   * 获取用户核心记忆列表
   * @param {string} userId - 用户 ID
   * @param {number} limit - 返回数量限制
   * @returns {Promise<Array>} 核心记忆列表
   */
  static async getCoreMemories(userId, limit = 50) {
    try {
      const response = await fetch(`${INTERACTION_API_BASE_URL}/memory/${userId}/core?limit=${limit}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || response.statusText);
      }
      return data;
    } catch (error) {
      console.error('Error fetching core memories:', error);
      throw error;
    }
  }

  /**
   * 设置或更新用户核心记忆
   * @param {string} userId - 用户 ID
   * @param {string} key - 记忆键
   * @param {any} value - 记忆值
   * @returns {Promise<Object>} 设置结果
   */
  static async setCoreMemory(userId, key, value) {
    try {
      const response = await fetch(`${INTERACTION_API_BASE_URL}/memory/${userId}/core`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ key, value })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || response.statusText);
      }
      return data;
    } catch (error) {
      console.error('Error setting core memory:', error);
      throw error;
    }
  }

  /**
   * 删除用户核心记忆
   * @param {string} userId - 用户 ID
   * @param {string} key - 记忆键
   * @returns {Promise<Object>} 删除结果
   */
  static async deleteCoreMemory(userId, key) {
    try {
      const response = await fetch(`${INTERACTION_API_BASE_URL}/memory/${userId}/core/${key}`, {
        method: 'DELETE'
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || response.statusText);
      }
      return data;
    } catch (error) {
      console.error('Error deleting core memory:', error);
      throw error;
    }
  }
}

export default RAGAPI;