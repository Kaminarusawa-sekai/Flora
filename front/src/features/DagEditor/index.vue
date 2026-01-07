<template>
  <div class="relative w-full h-full">
    <!-- 背景：深空渐变 + 网格 -->
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.03),transparent_70%)] pointer-events-none"></div>
    <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMwLTkuOTQtOC4wNi0xOC0xOC0xOCA5Ljk0IDAgMTggOC4wNiAxOCAxOCAwIDkuOTQtOC4wNiAxOC0xOCAxOHptMCAzMGMwLTkuOTQtOC4wNi0xOC0xOC0xOCA5Ljk0IDAgMTggOC4wNiAxOCAxOCAwIDkuOTQtOC4wNiAxOC0xOCAxOHptLTM2IDBjMC05Ljk0LTguMDYtMTgtMTgtMTggOS45NCAwIDE4IDguMDYgMTggMTggMCA5Ljk0LTguMDYgMTgtMTggMTh6Ii8+PC9nPjwvc3ZnPg==')] opacity-10 pointer-events-none"></div>
    
    <!-- Vue Flow 容器 - L0 -->
    <VueFlow
      v-model:edges="dagStore.edges"
      v-model:nodes="dagStore.nodes"
      v-model:selectedNodes="selectedNodes"
      :node-types="nodeTypes"
      class="bg-transparent h-full"
      :default-viewport="{ zoom: 1, x: 0, y: 0 }"
      @node-click="onNodeClick"
      @drag-start="onDragStart"
      @drag-end="onDragEnd"
      @connect="onConnect"
    >
      <!-- 默认插槽内容：包含 SVG 渐变、背景和控制器 -->
      <template #default>
        <!-- SVG 渐变定义 -->
        <svg style="position: absolute; width: 0; height: 0;">
          <defs>
            <linearGradient id="shockwave-gradient" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#3b82f6" stop-opacity="0" />
              <stop offset="50%" stop-color="#3b82f6" stop-opacity="1" />
              <stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
            </linearGradient>
            <linearGradient id="success-gradient" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stop-color="#10b981" stop-opacity="0" />
              <stop offset="50%" stop-color="#10b981" stop-opacity="1" />
              <stop offset="100%" stop-color="#10b981" stop-opacity="0" />
            </linearGradient>
          </defs>
        </svg>
        
        <!-- 背景 -->
        <Background pattern-color="#ffffff" :gap="24" :size="1" class="opacity-[0.03]" />
      </template>
    </VueFlow>

    <!-- 悬浮控制按钮 - L3 -->
    <div class="absolute top-4 right-4 z-10 flex gap-2">
      <GlassCard hoverable noPadding class="p-2 flex gap-2">
        <button class="p-2 text-gray-400 hover:text-white transition"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" /></svg></button>
        <button class="p-2 text-gray-400 hover:text-white transition"><svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" /></svg></button>
      </GlassCard>
    </div>

    <div class="absolute bottom-6 right-6 z-10">
      <GlassCard class="flex flex-col gap-4 p-3 backdrop-blur-2xl">
        <button class="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-sci-blue transition">
           <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
        </button>
        <button class="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white transition">
           <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg>
        </button>
      </GlassCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { VueFlow, addEdge, useVueFlow } from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import '@vue-flow/core/dist/style.css';
import GlassCard from '@/components/ui/GlassCard.vue';
import GlassNode from './nodes/GlassNode.vue';
import { useDagStore } from '@/stores/useDagStore';
import { getLatestTraceByRequest } from '@/api/order';
import ConversationAPI from '@/api/conversation';

// 接收 selectedTaskId 属性（这里实际上是 sessionId）
const props = defineProps<{
  selectedTaskId: string;
}>();

const dagStore = useDagStore();

// 获取 VueFlow 实例，用于控制视图
const { fitView, updateNodeInternals } = useVueFlow();

// 从 session info 获取 request_id，然后获取 trace_id，最后加载 DAG 数据
const loadDagForSession = async (sessionId: string) => {
  try {
    if (!sessionId) {
      console.error('Session ID is empty, using default DAG structure');
      // Session ID 为空，使用默认 DAG 结构
      const defaultDag = dagStore.getDefaultDag();
      
      // 正常加载数据
      dagStore.nodes = defaultDag.nodes;
      dagStore.edges = defaultDag.edges;
      
      // 等待 Vue 完成 DOM 更新
      await nextTick();
      
      // 强制 Vue Flow 重新测量所有节点的句柄位置
      if (dagStore.nodes.length > 0) {
        updateNodeInternals(dagStore.nodes.map(node => node.id));
      }
      
      // 使用 requestAnimationFrame 确保在下一帧调整视图
      window.requestAnimationFrame(() => {
        fitView({ padding: 0.2, duration: 800 });
        
        // 双重保险：动画帧里再触发一次连线更新
        updateNodeInternals(dagStore.nodes.map(node => node.id));
      });
      
      dagStore.selectedNodeId = null;
      return;
    }
    
    console.log('Loading DAG for session:', sessionId);
    
    // 1. 从 session info 中获取 request_id
    const sessionInfo = await ConversationAPI.getSessionInfo(sessionId);
    const requestId = sessionInfo.request_id;
    
    if (!requestId) {
      console.error('Request ID not found in session info, using initial DAG structure');
      // Request ID 不存在，使用初始 DAG 结构
      const initialDag = dagStore.getInitialDag();
      
      // 正常加载数据
      dagStore.nodes = initialDag.nodes;
      dagStore.edges = initialDag.edges;
      
      // 等待 Vue 完成 DOM 更新
      await nextTick();
      
      // 强制 Vue Flow 重新测量所有节点的句柄位置
      if (dagStore.nodes.length > 0) {
        updateNodeInternals(dagStore.nodes.map(node => node.id));
      }
      
      // 使用 requestAnimationFrame 确保在下一帧调整视图
      window.requestAnimationFrame(() => {
        fitView({ padding: 0.2, duration: 800 });
        
        // 双重保险：动画帧里再触发一次连线更新
        updateNodeInternals(dagStore.nodes.map(node => node.id));
      });
      
      dagStore.selectedNodeId = null;
      return;
    }
    
    console.log('Got request_id:', requestId);
    
    // 2. 通过 request_id 获取 trace_id
    const traceInfo = await getLatestTraceByRequest(requestId);
    const traceId = traceInfo.trace_id;
    
    if (!traceId) {
      console.error('Trace ID not found for request:', requestId, 'using initial DAG structure');
      // Trace ID 不存在，使用初始 DAG 结构
      const initialDag = dagStore.getInitialDag();
      
      // 正常加载数据
      dagStore.nodes = initialDag.nodes;
      dagStore.edges = initialDag.edges;
      
      // 等待 Vue 完成 DOM 更新
      await nextTick();
      
      // 强制 Vue Flow 重新测量所有节点的句柄位置
      if (dagStore.nodes.length > 0) {
        updateNodeInternals(dagStore.nodes.map(node => node.id));
      }
      
      // 使用 requestAnimationFrame 确保在下一帧调整视图
      window.requestAnimationFrame(() => {
        fitView({ padding: 0.2, duration: 800 });
        
        // 双重保险：动画帧里再触发一次连线更新
        updateNodeInternals(dagStore.nodes.map(node => node.id));
      });
      
      dagStore.selectedNodeId = null;
      return;
    }
    
    console.log('Got trace_id:', traceId);
    
    // 3. 使用 trace_id 加载 DAG 数据
    await dagStore.loadDagByTraceId(traceId);
    
    // 等待 Vue 完成 DOM 更新
    await nextTick();
    
    // 强制 Vue Flow 重新测量所有节点的句柄位置
    if (dagStore.nodes.length > 0) {
      updateNodeInternals(dagStore.nodes.map(node => node.id));
    }
    
    // 使用 requestAnimationFrame 确保在下一帧调整视图
    window.requestAnimationFrame(() => {
      fitView({ padding: 0.2, duration: 800 });
      
      // 双重保险：动画帧里再触发一次连线更新
      updateNodeInternals(dagStore.nodes.map(node => node.id));
    });
  } catch (error) {
    console.error('Failed to load DAG for session:', error, 'using default DAG structure');
    // 发生错误，使用默认 DAG 结构
    const defaultDag = dagStore.getDefaultDag();
    
    // 正常加载数据
    dagStore.nodes = defaultDag.nodes;
    dagStore.edges = defaultDag.edges;
    
    // 等待 Vue 完成 DOM 更新
    await nextTick();
    
    // 强制 Vue Flow 重新测量所有节点的句柄位置
    if (dagStore.nodes.length > 0) {
      updateNodeInternals(dagStore.nodes.map(node => node.id));
    }
    
    // 使用 requestAnimationFrame 确保在下一帧调整视图
    window.requestAnimationFrame(() => {
      fitView({ padding: 0.2, duration: 800 });
      
      // 双重保险：动画帧里再触发一次连线更新
      updateNodeInternals(dagStore.nodes.map(node => node.id));
    });
    
    dagStore.selectedNodeId = null;
  }
};

// 监听 selectedTaskId 变化（这里实际上是 sessionId），更新 DAG 数据
watch(
  () => props.selectedTaskId,
  (newSessionId) => {
    loadDagForSession(newSessionId);
  },
  { immediate: true } // 立即执行一次
);

// 自定义节点类型
const nodeTypes = {
  'glass': GlassNode as any,
};

// 选中的节点
const selectedNodes = ref<string[]>([]);

// 节点点击事件
const onNodeClick = (event: any) => {
  console.log('Node clicked:', event.node.id);
  dagStore.selectNode(event.node.id);
};

// 拖拽开始事件
const onDragStart = () => {
  dagStore.setDragging(true);
};

// 拖拽结束事件
const onDragEnd = () => {
  dagStore.setDragging(false);
};

// 连接事件
const onConnect = (params: any) => {
  const newEdge = addEdge(
    { ...params, animated: true },
    dagStore.edges
  );
  // 类型断言，解决类型不匹配问题
  dagStore.edges = newEdge as any;
};
</script>

<style scoped>
/* --- 连线特效优化 --- */
/* 普通连线 */
:deep(.vue-flow__edge-path) {
  stroke: #3f3f46;
  stroke-width: 2;
  filter: drop-shadow(0 0 4px rgba(59, 130, 246, 0.3));
}

/* 冲击波连线：高亮的实体光束 */
:deep(.vue-flow__edge.shockwave path) {
  stroke: url(#shockwave-gradient) !important; /* 使用SVG渐变 */
  stroke-width: 4;
  filter: drop-shadow(0 0 8px rgba(59, 130, 246, 0.6));
  stroke-dasharray: 20;
  animation: beam-flow 0.5s linear infinite;
}

@keyframes beam-flow {
  to { stroke-dashoffset: -40; }
}

/* 成功状态连线 */
:deep(.vue-flow__edge.success path) {
  stroke: url(#success-gradient) !important;
  stroke-width: 4;
  filter: drop-shadow(0 0 8px rgba(16, 185, 129, 0.6));
  stroke-dasharray: 20;
  animation: beam-flow 0.5s linear infinite;
}

/* 死亡状态连线 */
:deep(.vue-flow__edge.dead path) {
  stroke: #3f3f46 !important;
  opacity: 0.5;
}

/* 节点被击中时的故障抖动 */
:deep(.node-glitch) {
  animation: glitch-anim 0.3s cubic-bezier(.25, .46, .45, .94) both infinite;
  color: #3b82f6 !important;
  border-color: #3b82f6 !important;
  background: rgba(59, 130, 246, 0.1) !important;
}

@keyframes glitch-anim {
  0% { transform: translate(0) }
  20% { transform: translate(-2px, 2px) }
  40% { transform: translate(-2px, -2px) }
  60% { transform: translate(2px, 2px) }
  80% { transform: translate(2px, -2px) }
  100% { transform: translate(0) }
}

/* 节点样式优化 */
:deep(.vue-flow__node) {
  filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.2));
}
</style>