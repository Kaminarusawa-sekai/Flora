<script setup lang="ts">
import { computed } from 'vue';
import { Handle, Position } from '@vue-flow/core';

interface NodeData {
  id: string;
  label: string;
  type: string;
  status: 'idle' | 'running' | 'success' | 'error' | 'killed';
  progress: number;
  time: number;
  childrenCount?: number;
}

const props = defineProps<{
  data: NodeData;
  selected: boolean;
  class?: string;
}>();

// 状态逻辑
const isRunning = computed(() => props.data.status === 'running');
const isFailed = computed(() => props.data.status === 'error');
const isKilled = computed(() => props.data.status === 'killed');
const isSuccess = computed(() => props.data.status === 'success');

// 进度条样式
const progressStyle = computed(() => ({
  width: `${props.data.progress}%`
}));

// 计算子节点数量
const childrenCount = computed(() => {
  return props.data.childrenCount || 0;
});
</script>

<template>
  <div 
    class="glass-card w-[280px] p-5 relative group overflow-hidden"
    :class="{ 
      'selected': selected, 
      'card-killed': isKilled,
      'status-running': isRunning,
      'status-success': isSuccess,
      'status-failed': isFailed 
    }"
  >
    <Handle type="target" :position="Position.Top" class="!opacity-0 !w-full !h-4 !top-0" />

    <div class="flex justify-between items-start mb-2">
      <div class="flex flex-col">
        <div class="flex items-center gap-2 mb-1">
          <!-- 状态图标 -->
          <div v-if="isRunning" class="w-5 h-5 flex items-center justify-center">
            <svg class="animate-spin h-5 w-5 text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          
          <div v-else-if="isFailed" class="w-5 h-5 flex items-center justify-center text-rose-500">
             <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
               <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
             </svg>
          </div>
          
          <div v-else-if="isSuccess" class="w-5 h-5 flex items-center justify-center text-emerald-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          </div>
          
          <div v-else class="w-5 h-5 flex items-center justify-center text-amber-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
          </div>
        </div>
        
        <span class="text-xs font-medium text-gray-400 tracking-wide uppercase">{{ data.type }} NODE</span>
        <h3 class="text-base font-bold text-white leading-tight mt-0.5">{{ data.label }}</h3>
      </div>
      
      <div class="px-2 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] text-gray-400 backdrop-blur-md">
        #{{ data.id }}
      </div>
    </div>

    <div class="mt-4 mb-3">
      <div class="text-4xl font-bold tracking-tight text-white flex items-baseline gap-1">
        {{ data.progress }}<span class="text-xl text-gray-500 font-normal">%</span>
      </div>
    </div>

    <div class="relative h-3 w-full bg-white/10 rounded-full overflow-hidden mb-4">
      <div 
        class="absolute top-0 left-0 h-full rounded-full transition-all duration-700 ease-out"
        :class="isFailed || isKilled ? 'gradient-bar-failed' : 'gradient-bar-success'"
        :style="progressStyle"
      ></div>
      <div 
        class="absolute top-0 left-0 h-full w-full opacity-50 blur-[8px]"
        :class="isFailed || isKilled ? 'bg-rose-500' : 'bg-teal-400'"
        :style="{ width: data.progress + '%', opacity: 0.3 }"
      ></div>
    </div>

    <div class="flex items-center justify-between pt-3 border-t border-white/5">
      <div class="flex -space-x-2">
        <div class="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 border border-[#1e1e23]"></div>
        <div class="w-6 h-6 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 border border-[#1e1e23]"></div>
        <div v-if="childrenCount > 0" class="w-6 h-6 rounded-full bg-[#2a2a30] border border-[#1e1e23] flex items-center justify-center text-[8px] text-gray-400">
          +{{ childrenCount }}
        </div>
      </div>

      <div class="text-[10px] font-mono text-gray-500 flex items-center gap-1">
        <span>{{ data.time }}ms</span>
      </div>
    </div>

    <Handle type="source" :position="Position.Bottom" class="!opacity-0 !w-full !h-4 !bottom-0" />
    
    <div v-if="isKilled" class="absolute inset-0 bg-black/60 backdrop-blur-[1px] z-10 flex items-center justify-center">
        <span class="text-rose-500 font-bold tracking-widest border border-rose-500/30 px-3 py-1 rounded bg-rose-500/10">TERMINATED</span>
    </div>
  </div>
</template>

<style scoped>
/* 毛玻璃节点样式 */
.glass-card {
  background: rgba(30, 30, 35, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 
    0 20px 40px -10px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

/* 选中态 */
.glass-card.selected {
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 
    0 0 0 4px rgba(255, 255, 255, 0.05),
    0 20px 40px -10px rgba(0, 0, 0, 0.7);
  transform: translateY(-2px) scale(1.02);
}

/* 进度条样式 */
.gradient-bar-success {
  background: linear-gradient(90deg, #4ade80 0%, #2dd4bf 50%, #3b82f6 100%);
  box-shadow: 0 0 20px rgba(45, 212, 191, 0.4);
}

.gradient-bar-failed {
  background: linear-gradient(90deg, #f87171 0%, #f43f5e 50%, #e11d48 100%);
  box-shadow: 0 0 20px rgba(244, 63, 94, 0.4);
}

/* 状态样式 */
.status-running {
  border-color: rgba(45, 212, 191, 0.5);
  box-shadow: 0 0 10px rgba(45, 212, 191, 0.2);
}

.status-success {
  border-color: rgba(74, 222, 128, 0.5);
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.2);
}

.status-failed {
  border-color: rgba(244, 63, 94, 0.5);
  box-shadow: 0 0 10px rgba(244, 63, 94, 0.2);
}

/* 死亡状态 */
.card-killed {
  filter: grayscale(1) brightness(0.5);
  border-color: rgba(255, 50, 50, 0.3);
  transform: scale(0.95);
}
</style>