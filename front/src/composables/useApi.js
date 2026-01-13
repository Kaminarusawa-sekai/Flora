import { ref, onUnmounted, unref } from 'vue';
import { apiClient } from '../api/order';
import { createSSEClient, getConversationStreamUrl } from '../utils/sse';
import { createWebSocketClient, getTraceWebSocketUrl } from '../utils/socket';

/**
 * 通用 API 组合函数
 * @returns {Object} API 相关的方法和状态
 */
export function useApi() {
  return {
    api: apiClient,
  };
}

/**
 * 对话 SSE 组合函数
 * @param {string} sessionId - 会话 ID
 * @param {Object} options - 配置选项
 * @returns {Object} SSE 相关的方法和状态
 */
export function useConversationSSE(sessionIdRef, options = {}) {
  const sseClient = ref(null);
  const isConnected = ref(false);
  const events = ref([]);

  const initializeSSE = async () => {
    const resolvedSessionId =
      typeof sessionIdRef === 'function' ? sessionIdRef() : unref(sessionIdRef);
    if (!resolvedSessionId) return;

    const url = getConversationStreamUrl(resolvedSessionId);
    const customEvents = (options.events || []).filter(
      (eventType) => !['message', 'done', 'error', 'open'].includes(eventType)
    );
    sseClient.value = createSSEClient(url, {
      events: ['done', 'error', ...(options.events || [])],
      maxReconnectAttempts: options.maxReconnectAttempts || 5,
      reconnectDelay: options.reconnectDelay || 1000,
    });

    sseClient.value.on('open', () => {
      isConnected.value = true;
      if (options.onOpen) options.onOpen();
    });

    sseClient.value.on('message', (data) => {
      events.value.push({ type: 'message', data });
      if (options.onMessage) options.onMessage(data);
    });

    sseClient.value.on('done', (data) => {
      events.value.push({ type: 'done', data });
      if (options.onDone) options.onDone(data);
    });

    sseClient.value.on('error', (error) => {
      events.value.push({ type: 'error', data: error });
      if (options.onError) options.onError(error);
    });

    customEvents.forEach((eventType) => {
      sseClient.value.on(eventType, (data) => {
        events.value.push({ type: eventType, data });
        if (options.onEvent) options.onEvent(eventType, data);
        if (eventType === 'thought' && options.onThought) options.onThought(data);
        if (eventType === 'meta' && options.onMeta) options.onMeta(data);
      });
    });

    await sseClient.value.connect();
  };

  const disconnect = () => {
    if (sseClient.value) {
      sseClient.value.close();
      sseClient.value = null;
      isConnected.value = false;
    }
  };

  onUnmounted(() => {
    disconnect();
  });

  return {
    sseClient,
    isConnected,
    events,
    initializeSSE,
    disconnect,
  };
}

/**
 * Trace WebSocket 组合函数
 * @param {string} traceId - Trace ID
 * @param {Object} options - 配置选项
 * @returns {Object} WebSocket 相关的方法和状态
 */
export function useTraceWebSocket(traceId, options = {}) {
  const wsClient = ref(null);
  const isConnected = ref(false);
  const messages = ref([]);

  const initializeWebSocket = async () => {
    if (!traceId) return;

    const url = getTraceWebSocketUrl(traceId);
    wsClient.value = createWebSocketClient(url, {
      protocols: options.protocols || [],
      maxReconnectAttempts: options.maxReconnectAttempts || 5,
      reconnectDelay: options.reconnectDelay || 1000,
    });

    wsClient.value.on('open', () => {
      isConnected.value = true;
      if (options.onOpen) options.onOpen();
    });

    wsClient.value.on('message', (data) => {
      messages.value.push(data);
      if (options.onMessage) options.onMessage(data);
    });

    wsClient.value.on('close', (event) => {
      isConnected.value = false;
      if (options.onClose) options.onClose(event);
    });

    wsClient.value.on('error', (error) => {
      if (options.onError) options.onError(error);
    });

    await wsClient.value.connect();
  };

  const sendMessage = (message) => {
    if (wsClient.value && isConnected.value) {
      return wsClient.value.send(message);
    }
    return false;
  };

  const disconnect = () => {
    if (wsClient.value) {
      wsClient.value.close();
      wsClient.value = null;
      isConnected.value = false;
    }
  };

  onMounted(() => {
    initializeWebSocket();
  });

  onUnmounted(() => {
    disconnect();
  });

  return {
    wsClient,
    isConnected,
    messages,
    initializeWebSocket,
    sendMessage,
    disconnect,
  };
}

/**
 * 任务管理组合函数
 * @returns {Object} 任务管理相关的方法
 */
export function useTaskManagement() {
  const loading = ref(false);
  const error = ref(null);

  const fetchTasksInTrace = async (traceId, filters = {}) => {
    loading.value = true;
    error.value = null;
    try {
      return await apiClient.listTasksInTrace(traceId, filters);
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchTraceGraph = async (traceId) => {
    loading.value = true;
    error.value = null;
    try {
      return await apiClient.getTraceTopology(traceId);
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchTraceStatus = async (traceId) => {
    loading.value = true;
    error.value = null;
    try {
      return await apiClient.getTraceStatus(traceId);
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchTaskDetail = async (taskId, expandPayload = false) => {
    loading.value = true;
    error.value = null;
    try {
      return await apiClient.getTaskDetail(taskId, expandPayload);
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const fetchReadyTasks = async () => {
    loading.value = true;
    error.value = null;
    try {
      return await apiClient.getReadyTasks();
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    loading,
    error,
    fetchTasksInTrace,
    fetchTraceGraph,
    fetchTraceStatus,
    fetchTaskDetail,
    fetchReadyTasks,
  };
}
