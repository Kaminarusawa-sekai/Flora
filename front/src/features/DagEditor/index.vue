<template>
  <div class="w-full h-full relative modern-bg overflow-hidden">
    <!-- 背景噪点 -->
    <div class="noise-overlay"></div>
    
    <!-- Vue Flow 容器 -->
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
              <stop offset="0%" stop-color="#f43f5e" stop-opacity="0" />
              <stop offset="50%" stop-color="#f43f5e" stop-opacity="1" />
              <stop offset="100%" stop-color="#f43f5e" stop-opacity="0" />
            </linearGradient>
          </defs>
        </svg>
        
        <!-- 背景 -->
        <Background pattern-color="#ffffff" :gap="24" :size="1" class="opacity-[0.03]" />
        
        <!-- 控制器 -->
        <Controls class="!bg-slate-800/80 !backdrop-blur-md !border-slate-600/50 !fill-white/80" />
      </template>
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import {
  VueFlow,
  addEdge,
} from '@vue-flow/core';
import { Background } from '@vue-flow/background';
import { Controls } from '@vue-flow/controls';
import '@vue-flow/core/dist/style.css';
import GlassNode from './nodes/GlassNode.vue';
import { useDagStore } from '@/stores/useDagStore';

const dagStore = useDagStore();

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
/* 背景样式 */
.modern-bg {
  background: 
    radial-gradient(circle at 15% 50%, rgba(76, 29, 149, 0.08), transparent 40%),
    radial-gradient(circle at 85% 30%, rgba(16, 185, 129, 0.05), transparent 40%);
  background-color: #09090b;
}

/* 叠加噪点纹理增加质感 */
.noise-overlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
}

/* --- 连线特效优化 --- */
/* 普通连线 */
:deep(.vue-flow__edge-path) {
  stroke: #3f3f46;
  stroke-width: 2;
}

/* 冲击波连线：高亮的实体光束 */
:deep(.vue-flow__edge.shockwave path) {
  stroke: url(#shockwave-gradient) !important; /* 使用SVG渐变 */
  stroke-width: 4;
  filter: drop-shadow(0 0 8px rgba(244, 63, 94, 0.6));
  stroke-dasharray: 20;
  animation: beam-flow 0.5s linear infinite;
}

@keyframes beam-flow {
  to { stroke-dashoffset: -40; }
}

/* 死亡状态连线 */
:deep(.vue-flow__edge.dead path) {
  stroke: #3f3f46 !important;
  opacity: 0.5;
}

/* 节点被击中时的故障抖动 */
:deep(.node-glitch) {
  animation: glitch-anim 0.3s cubic-bezier(.25, .46, .45, .94) both infinite;
  color: #f43f5e !important;
  border-color: #f43f5e !important;
  background: rgba(244, 63, 94, 0.1) !important;
}

@keyframes glitch-anim {
  0% { transform: translate(0) }
  20% { transform: translate(-2px, 2px) }
  40% { transform: translate(-2px, -2px) }
  60% { transform: translate(2px, 2px) }
  80% { transform: translate(2px, -2px) }
  100% { transform: translate(0) }
}
</style>