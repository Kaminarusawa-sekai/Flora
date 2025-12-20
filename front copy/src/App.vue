<script setup>
import { ref, onMounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import ModernNode from './components/ModernNode.vue'
import '@vue-flow/core/dist/style.css'

// --- 数据状态 ---
const nodes = ref([])
const edges = ref([])
const selectedNode = ref(null)
const globalStatus = ref({ id: 'X9-S8-ALPHA', progress: 45, status: 'RUNNING' })

// --- 自动布局逻辑 (手动布局，避免 dagre 版本兼容性问题) ---
const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  // 简单的手动布局，按层级排列节点
  const nodePositions = {
    '1': { x: 200, y: 50 },
    '2': { x: 100, y: 300 },
    '3': { x: 300, y: 300 },
    '4': { x: 50, y: 550 },
    '5': { x: 150, y: 550 },
  }

  return nodes.map((node) => ({
    ...node,
    position: nodePositions[node.id] || { x: 0, y: 0 },
  }))
}

// --- 初始化模拟数据 ---
const initGraph = () => {
  const initialNodes = [
    { 
      id: '1', 
      type: 'custom', 
      data: { 
        label: 'Root Agent', 
        type: 'AGENT', 
        status: 'RUNNING', 
        progress: 45, 
        time: 0,
        childrenCount: 2
      } 
    },
    { 
      id: '2', 
      type: 'custom', 
      data: { 
        label: 'Data Group A', 
        type: 'AGENT', 
        status: 'SUCCESS', 
        progress: 100, 
        time: 120,
        childrenCount: 2
      } 
    },
    { 
      id: '3', 
      type: 'custom', 
      data: { 
        label: 'Data Group B', 
        type: 'AGENT', 
        status: 'RUNNING', 
        progress: 30, 
        time: 450,
        childrenCount: 0
      } 
    },
    { 
      id: '4', 
      type: 'custom', 
      data: { 
        label: 'Worker 01', 
        type: 'WORKER', 
        status: 'SUCCESS', 
        progress: 100, 
        time: 20,
        childrenCount: 0
      } 
    },
    { 
      id: '5', 
      type: 'custom', 
      data: { 
        label: 'Worker 02', 
        type: 'WORKER', 
        status: 'FAILED', 
        progress: 80, 
        time: 200,
        childrenCount: 0
      } 
    },
  ]
  const initialEdges = [
    { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#4ade80' } },
    { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#2dd4bf' } },
    { id: 'e2-4', source: '2', target: '4', animated: false, style: { stroke: '#4ade80' } },
    { id: 'e2-5', source: '2', target: '5', animated: false, style: { stroke: '#f43f5e' } },
  ]
  
  nodes.value = getLayoutedElements(initialNodes, initialEdges)
  edges.value = initialEdges
}

// --- 事件处理 ---
const onNodeClick = (event) => {
  selectedNode.value = event.node.data
  selectedNode.value.fullId = event.node.id
}

// 使用 useVueFlow 获取实例操作方法
const { findNode } = useVueFlow()

/**
 * 触发级联熔断 (Cascade Kill)
 * @param {string} startNodeId - 起始节点ID
 */
const triggerShockwave = async (startNodeId) => {
  console.log(`[COMMAND] Initiating Kill Sequence on Node: ${startNodeId}`)
  
  // 递归函数
  const propagate = async (currentId) => {
    const currentNode = findNode(currentId)
    if (!currentNode || currentNode.data.status === 'KILLED') return

    // 1. 处决当前节点 (更新数据 + 视觉)
    currentNode.data.status = 'KILLED'
    // 添加故障动画类
    currentNode.class = 'node-glitch'
    
    // 0.5秒后移除抖动，保持死亡状态
    setTimeout(() => {
      currentNode.class = 'opacity-50 grayscale border-slate-700' // 变成尸体样式
    }, 500)

    // 2. 寻找连线
    const outgoingEdges = edges.value.filter(e => e.source === currentId)
    if (outgoingEdges.length === 0) return

    // 3. 激活连线冲击波
    outgoingEdges.forEach(e => {
      e.class = 'shockwave' // 应用 CSS 动画类
      e.animated = true
    })

    // 4. 等待传输时间 (制造层级感)
    await new Promise(r => setTimeout(r, 300)) // 300ms 传导一层

    // 5. 递归向下
    // 使用 Promise.all 并行处理所有分支
    const promises = outgoingEdges.map(async (e) => {
      // 连线熄灭
      e.class = 'dead'
      e.animated = false
      // 击中下一个节点
      await propagate(e.target)
    })
    
    await Promise.all(promises)
  }

  // 开始执行
  await propagate(startNodeId)
}

/**
 * 全局紧急停止功能
 */
const triggerGlobalKill = async () => {
  console.log(`[EMERGENCY] Initiating Global Kill Sequence`)
  
  // 依次触发所有根节点的冲击波
  const rootNodes = nodes.value.filter(node => {
    // 假设根节点是没有入边的节点
    return !edges.value.some(edge => edge.target === node.id)
  })
  
  for (const rootNode of rootNodes) {
    await triggerShockwave(rootNode.id)
  }
}

// 绑定到按钮
const handleCancel = () => {
  if (selectedNode.value) {
    triggerShockwave(selectedNode.value.fullId) // 注意：这里用的是 node.id
  }
}

onMounted(() => {
  initGraph()
})
</script>

<template>
  <div class="h-screen w-full modern-bg text-white overflow-hidden relative font-sans">
    <!-- 背景噪点 -->
    <div class="noise-overlay"></div>

    <!-- 导航栏 -->
    <nav class="absolute top-6 left-6 right-6 h-16 rounded-2xl glass-card flex items-center justify-between px-6 z-50">
      <div class="flex items-center gap-4">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 shadow-lg shadow-cyan-500/30 flex items-center justify-center">
          <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
        </div>
        <div>
          <h1 class="font-bold text-sm tracking-wide">FRACTAL COMMAND</h1>
          <div class="text-[10px] text-gray-400 flex items-center gap-2">
             <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
             System Online
          </div>
        </div>
      </div>

      <div class="flex items-center gap-6">
         <div class="text-center">
           <div class="text-[10px] text-gray-500 uppercase font-bold">Total Nodes</div>
           <div class="text-sm font-mono font-medium">{{ nodes.length }}</div>
         </div>
         <div class="w-px h-6 bg-white/10"></div>
         <div class="text-center">
           <div class="text-[10px] text-gray-500 uppercase font-bold">Progress</div>
           <div class="text-sm font-mono font-medium text-cyan-400">{{ globalStatus.progress }}%</div>
         </div>
      </div>

      <div class="flex gap-3">
         <button class="px-4 py-2 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 text-gray-300 transition-all border border-white/5">
           Settings
         </button>
         <button 
            @click="triggerGlobalKill"
            class="px-4 py-2 rounded-xl text-xs font-semibold bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/20 transition-all shadow-[0_0_15px_rgba(244,63,94,0.2)]"
         >
           EMERGENCY STOP
         </button>
      </div>
    </nav>

    <!-- 主内容区 -->
    <div class="absolute inset-0 pt-24 pb-6 pl-6 pr-6 overflow-hidden">
      <VueFlow 
        v-model:nodes="nodes" 
        v-model:edges="edges"
        class="bg-transparent h-full"
        :default-viewport="{ zoom: 1, x: 0, y: 0 }"
        @node-click="onNodeClick"
      >
        <!-- 自定义节点模板 -->
        <template #node-custom="props">
          <ModernNode v-bind="props" />
        </template>
        
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

    <!-- 右侧详情面板 -->
    <aside class="absolute top-24 right-6 bottom-6 w-96 glass-card p-6 overflow-y-auto z-40 transition-all duration-300 transform translate-x-0">
      <div v-if="selectedNode" class="h-full flex flex-col">
        <div class="mb-6">
          <h2 class="text-xl font-bold text-white mb-1">{{ selectedNode.label }}</h2>
          <div class="flex gap-2 text-[10px] text-gray-400 mt-1">
            <span class="bg-white/5 px-2 py-1 rounded-full backdrop-blur-md">ID: {{ selectedNode.fullId }}</span>
            <span class="bg-white/5 px-2 py-1 rounded-full backdrop-blur-md">{{ selectedNode.type }}</span>
            <span class="bg-white/5 px-2 py-1 rounded-full backdrop-blur-md">{{ selectedNode.status }}</span>
          </div>
        </div>

        <div class="flex-1 space-y-6 font-mono text-sm">
          
          <div>
            <h3 class="text-xs text-gray-500 uppercase mb-3 border-b border-white/5 pb-2 flex items-center justify-between">
              <span>Input Parameters</span>
              <button class="text-[10px] text-gray-400 hover:text-gray-300 transition-colors">
                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </button>
            </h3>
            <div class="bg-white/5 p-3 text-green-400 text-xs rounded-lg border border-white/5 backdrop-blur-md">
              {
                "target_url": "api/v1/scan",
                "retry_limit": 3,
                "timeout": 5000
              }
            </div>
          </div>

          <div>
            <h3 class="text-xs text-gray-500 uppercase mb-3 border-b border-white/5 pb-2 flex items-center justify-between">
              <span>Live Telemetry</span>
              <div class="flex items-center gap-2">
                <span class="text-[10px] text-green-400 flex items-center gap-1">
                  <span class="w-1 h-1 rounded-full bg-green-400 animate-pulse"></span>
                  Streaming
                </span>
              </div>
            </h3>
            <div class="bg-black/30 p-3 text-[10px] font-mono overflow-y-auto border border-white/5 text-gray-300 leading-tight rounded-lg max-h-48 backdrop-blur-md">
              <p><span class="text-cyan-400">[12:00:01]</span> Node initialized.</p>
              <p><span class="text-cyan-400">[12:00:02]</span> Fetching resources...</p>
              <p><span class="text-yellow-400">[12:00:03]</span> Warn: Latency spike detected.</p>
              <p><span class="text-cyan-400">[12:00:04]</span> Sub-task dispatched to Worker #05.</p>
              <p><span class="text-cyan-400">[12:00:05]</span> Processing data batch #1234...</p>
              <p><span class="text-cyan-400">[12:00:06]</span> 85% complete, 1.2s remaining.</p>
              <p class="animate-pulse">_</p>
            </div>
          </div>

          <div>
            <h3 class="text-xs text-gray-500 uppercase mb-3 border-b border-white/5 pb-2">
              Performance Metrics
            </h3>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-white/5 p-3 rounded-lg border border-white/5 backdrop-blur-md">
                <div class="text-[10px] text-gray-400 mb-1">Execution Time</div>
                <div class="text-lg font-bold text-white">{{ selectedNode.time }}ms</div>
              </div>
              <div class="bg-white/5 p-3 rounded-lg border border-white/5 backdrop-blur-md">
                <div class="text-[10px] text-gray-400 mb-1">Progress</div>
                <div class="text-lg font-bold text-white">{{ selectedNode.progress }}%</div>
              </div>
              <div class="bg-white/5 p-3 rounded-lg border border-white/5 backdrop-blur-md col-span-2">
                <div class="text-[10px] text-gray-400 mb-2">Memory Usage</div>
                <div class="relative h-2 w-full bg-white/10 rounded-full overflow-hidden">
                  <div class="absolute top-0 left-0 h-full bg-gradient-to-r from-cyan-400 to-blue-500 w-[65%] rounded-full"></div>
                </div>
              </div>
            </div>
          </div>

        </div>

        <div class="pt-6 border-t border-white/5 mt-6">
          <div class="grid grid-cols-2 gap-3">
            <button @click="handleCancel" class="col-span-1 bg-transparent border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 py-2.5 text-xs font-bold uppercase transition-colors rounded-xl">
              Cancel Node
            </button>
            <button class="col-span-1 bg-gradient-to-r from-cyan-500 to-blue-600 text-white py-2.5 text-xs font-bold uppercase transition-colors rounded-xl shadow-lg shadow-cyan-500/20">
              Retry
            </button>
          </div>
        </div>
      </div>
      
      <div v-else class="h-full flex items-center justify-center text-gray-500 text-xs text-center p-10">
        SELECT A NODE FROM THE <br>TACTICAL MAP TO INSPECT
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* 辅助样式 */
aside {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) rgba(255, 255, 255, 0.05);
}
</style>
