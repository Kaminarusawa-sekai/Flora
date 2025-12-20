<script setup>
import { Handle, Position } from '@vue-flow/core'
import { computed } from 'vue'

const props = defineProps(['data', 'selected', 'class']) // 接收 node.class 属性

// 根据状态计算动态类名
const statusClass = computed(() => {
  switch (props.data.status) {
    case 'RUNNING': return 'status-running bg-slate-900/80 animate-pulse-slow'
    case 'SUCCESS': return 'status-success bg-emerald-900/20'
    case 'FAILED': return 'status-failed bg-rose-900/20'
    case 'KILLED': return 'border-red-900 text-red-900 bg-slate-900/80'
    default: return 'status-waiting bg-slate-900/50'
  }
})

// 进度条颜色
const progressColor = computed(() => {
  if (props.data.status === 'FAILED' || props.data.status === 'KILLED') {
    return 'bg-rose-500'
  }
  return 'bg-cyan-400'
})
</script>

<template>
  <div
    class="relative min-w-[220px] px-3 py-2 border-l-4 transition-all duration-300 group clip-corner bg-slate-900/90"
    :class="[statusClass, selected ? 'ring-2 ring-white scale-105 z-50' : 'border-slate-700', class]"
  >
    <!-- KILLED 状态覆盖层 -->
    <div v-if="data.status === 'KILLED'" class="absolute inset-0 flex items-center justify-center bg-black/80 z-10 backdrop-blur-sm text-red-600 font-black tracking-widest text-lg">
      KILLED
    </div>

    <Handle type="target" :position="Position.Top" class="!bg-white !w-3 !h-1 !rounded-none" />

    <div class="flex justify-between items-center mb-2 border-b border-white/10 pb-1">
      <div class="flex items-center gap-2">
        <span v-if="data.type === 'AGENT'" class="text-xs font-bold px-1 bg-white/10">AGT</span>
        <span v-else class="text-xs font-bold px-1 bg-white/10">WRK</span>
        <span class="text-xs font-bold tracking-wider uppercase">{{ data.label }}</span>
      </div>
      <span class="text-[10px] opacity-70">{{ data.id }}</span>
    </div>

    <div class="space-y-2">
      <div class="flex justify-between text-[10px] uppercase">
        <span>Process:</span>
        <span>{{ data.progress }}%</span>
      </div>
      <div class="h-1 w-full bg-slate-800 overflow-hidden relative">
        <div
          class="h-full transition-all duration-500 relative"
          :class="progressColor"
          :style="{ width: data.progress + '%' }"
        >
          <div class="absolute right-0 top-0 bottom-0 w-2 bg-white/50 blur-[2px]"></div>
        </div>
      </div>
      
      <div class="grid grid-cols-2 gap-1 text-[9px] text-slate-400 font-mono mt-1">
        <div>T: {{ data.time }}ms</div>
        <div class="text-right">{{ data.status }}</div>
      </div>
    </div>

    <div class="absolute top-0 right-0 w-2 h-2 border-t border-r border-current opacity-50"></div>
    <div class="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-current opacity-50"></div>

    <Handle type="source" :position="Position.Bottom" class="!bg-cyan-500 !w-3 !h-1 !rounded-none" />
  </div>
</template>