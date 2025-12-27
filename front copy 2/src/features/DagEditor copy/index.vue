<template>
  <div class="w-full h-full relative">
    <!-- Vue Flow 容器 -->
    <VueFlow
      v-model:edges="dagStore.edges"
      v-model:nodes="dagStore.nodes"
      v-model:selectedNodes="selectedNodes"
      :node-types="nodeTypes"
      class="w-full h-full"
      @node-click="onNodeClick"
      @drag-start="onDragStart"
      @drag-end="onDragEnd"
      @connect="onConnect"
    >
      <!-- 自定义背景网格 -->
      <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(59,130,246,0.03),transparent_70%)]"></div>
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import {
  VueFlow,
  addEdge,
} from '@vue-flow/core';
import '@vue-flow/core/dist/style.css';
import SciFiNode from './nodes/SciFiNode.vue';
import { useDagStore } from '@/stores/useDagStore';

const dagStore = useDagStore();

// 自定义节点类型
const nodeTypes = {
  'sci-fi': SciFiNode as any,
};

// 选中的节点
const selectedNodes = ref<string[]>([]);

// 节点点击事件
const onNodeClick = (node: any) => {
  console.log('Node clicked:', node.id);
  dagStore.selectNode(node.id);
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
/* Vue Flow 自定义样式 */
:deep(.vue-flow__node) {
  transform: translateZ(0);
}

:deep(.vue-flow__edge-path) {
  stroke: rgba(59, 130, 246, 0.5);
  stroke-width: 1.5;
}

:deep(.vue-flow__edge.selected .vue-flow__edge-path) {
  stroke: rgba(59, 130, 246, 0.8);
  stroke-width: 2;
}

:deep(.vue-flow__edge.animated .vue-flow__edge-path) {
  stroke-dasharray: 10;
  animation: dash 1s linear infinite;
}

@keyframes dash {
  from {
    stroke-dashoffset: 20;
  }
}

:deep(.vue-flow__minimap .vue-flow__node) {
  opacity: 0.5;
}
</style>
