<template>
  <Handle type="target" :position="'top' as any" class="!bg-sci-blue !w-2 !h-2" />
  
  <div class="dag-node" :class="data.status">
    <div class="flex items-center justify-between mb-2">
      <span class="text-xs font-mono text-gray-400">ID: {{ data.id }}</span>
      <StatusDot :status="data.status" />
    </div>
    
    <div class="text-sm font-bold text-gray-100">
      {{ data.label }}
    </div>
    
    <div class="mt-3 h-[2px] w-full bg-white/5 rounded-full overflow-hidden">
      <div 
        class="h-full bg-sci-blue shadow-[0_0_10px_#3b82f6] transition-all duration-500"
        :style="{ width: progress + '%' }"
      ></div>
    </div>
  </div>

  <Handle type="source" :position="'bottom' as any" class="!bg-sci-blue !w-2 !h-2" />
</template>

<script setup lang="ts">
import { Handle } from '@vue-flow/core';
import StatusDot from '@/components/ui/StatusDot.vue';
import { ref, onMounted } from 'vue';

const props = defineProps<{
  data: {
    id: string;
    label: string;
    status: 'idle' | 'running' | 'success' | 'error';
  };
}>();

const progress = ref(0);

onMounted(() => {
  if (props.data.status === 'running') {
    // 模拟进度变化
    const timer = setInterval(() => {
      progress.value += Math.random() * 10;
      if (progress.value >= 100) {
        clearInterval(timer);
        progress.value = 100;
      }
    }, 500);
  } else {
    progress.value = 100;
  }
});
</script>
