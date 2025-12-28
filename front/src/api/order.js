/**
 * API 基础配置
 */
const API_BASE_URL = 'http://localhost:8000/v1';

/**
 * 引入 DAG 转换工具函数
 */
import { transformTraceToDag } from '../utils/dagUtils';

/**
 * 通用请求函数
 * @param {string} url - 请求 URL
 * @param {Object} options - 请求选项
 * @returns {Promise<any>} 请求结果
 */
async function request(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // 添加认证头（如果有）
  const userId = localStorage.getItem('userId');
  if (userId) {
    headers['X-User-ID'] = userId;
  }

  const config = {
    ...options,
    headers,
  };

  const response = await fetch(`${API_BASE_URL}${url}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({
      message: response.statusText,
    }));
    throw new Error(error.message || `Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * 发送用户消息
 * @param {string} sessionId - 会话 ID
 * @param {Object} messageData - 消息数据
 * @param {string} messageData.utterance - 用户输入文本
 * @param {number} messageData.timestamp - 时间戳
 * @param {Object} messageData.metadata - 元数据
 * @returns {Promise<Object>} 响应结果
 */
export async function sendUserMessage(sessionId, messageData) {
  return request(`/conversations/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify(messageData),
  });
}

/**
 * 恢复中断的任务
 * @param {string} taskId - 任务 ID
 * @param {Object} resumeData - 恢复数据
 * @param {string} resumeData.slot_name - 待填充的槽位名称
 * @param {any} resumeData.value - 槽位值
 * @returns {Promise<Object>} 响应结果
 */
export async function resumeTask(taskId, resumeData) {
  return request(`/tasks/${taskId}/resume-with-input`, {
    method: 'POST',
    body: JSON.stringify(resumeData),
  });
}

/**
 * 列出 trace 内的任务
 * @param {string} traceId - Trace ID
 * @param {Object} filters - 过滤条件
 * @param {string} [filters.status] - 任务状态
 * @param {string} [filters.actor_type] - 执行角色类型
 * @param {number} [filters.layer] - 层级
 * @param {number} [filters.depth] - 深度
 * @param {string} [filters.role] - 角色
 * @param {number} [filters.limit=100] - 每页数量
 * @param {number} [filters.offset=0] - 偏移量
 * @returns {Promise<Array<Object>>} 任务列表
 */
export async function listTasksInTrace(traceId, filters = {}) {
  const queryParams = new URLSearchParams();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      queryParams.append(key, value);
    }
  });

  return request(`/traces/${traceId}/tasks?${queryParams.toString()}`);
}

/**
 * 获取 trace 拓扑图
 * @param {string} traceId - Trace ID
 * @returns {Promise<Object>} 转换后的拓扑图数据
 */
export async function getTraceTopology(traceId) {
  const traceData = await request(`/traces/${traceId}/graph`);
  return transformTraceToDag(traceData);
}

/**
 * 获取 trace 状态摘要
 * @param {string} traceId - Trace ID
 * @returns {Promise<Object>} 状态摘要
 */
export async function getTraceStatus(traceId) {
  return request(`/traces/${traceId}/status`);
}

/**
 * 获取任务详情
 * @param {string} taskId - 任务 ID
 * @param {boolean} [expandPayload=false] - 是否展开 payload
 * @returns {Promise<Object>} 任务详情
 */
export async function getTaskDetail(taskId, expandPayload = false) {
  return request(`/traces/tasks/${taskId}?expand_payload=${expandPayload}`);
}

/**
 * 获取就绪待执行的任务
 * @returns {Promise<Object>} 就绪任务列表，包含count和tasks字段
 */
export async function getReadyTasks() {
  return request('/traces/ready-tasks');
}

/**
 * 获取指定trace_id下的所有任务详情
 * @param {string} traceId - Trace ID
 * @param {boolean} [expandPayload=false] - 是否展开payload
 * @returns {Promise<Array<Object>>} 任务详情列表
 */
export async function getTraceDetail(traceId, expandPayload = false) {
  return request(`/traces/${traceId}/trace-details?expand_payload=${expandPayload}`);
}

/**
 * 根据request_id获取最新的trace_id
 * @param {string} requestId - 请求ID
 * @returns {Promise<Object>} 包含request_id和latest_trace_id的对象
 */
export async function getLatestTraceByRequest(requestId) {
  return request(`/commands/latest-by-request/${requestId}`);
}

/**
 * API 客户端对象，封装所有 API 方法
 */
export const apiClient = {
  // 对话相关
  sendUserMessage,
  resumeTask,
  
  // Trace 相关
  listTasksInTrace,
  getTraceTopology,
  getTraceStatus,
  getTaskDetail,
  getTraceDetail,
  getReadyTasks,
  
  // Commands 相关
  getLatestTraceByRequest,
};

export default apiClient;
