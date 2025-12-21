<template>
  <div class="inline-flex items-center gap-2">
    <div class="relative flex items-center justify-center">
      
      <span
        v-if="status === 'running' || status === 'pending'"
        class="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping"
        :class="statusColors[status].bg"
      ></span>

      <span
        class="relative inline-flex rounded-full transition-all duration-300"
        :class="[
          sizeConfig[size], 
          statusColors[status].bg,
          statusColors[status].shadow
        ]"
      ></span>
    </div>

    <span 
      v-if="showLabel || label" 
      class="font-mono uppercase tracking-wider font-medium transition-colors duration-300"
      :class="[
        textSizeConfig[size],
        statusColors[status].text
      ]"
    >
      <slot>{{ label || statusLabel }}</slot>
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

// 定义类型
type StatusType = 'running' | 'success' | 'error' | 'idle' | 'pending';
type SizeType = 'sm' | 'md' | 'lg';

const props = defineProps({
  status: {
    type: String as () => StatusType,
    required: true
  },
  size: {
    type: String as () => SizeType,
    default: 'sm'
  },
  showLabel: {
    type: Boolean,
    default: false
  },
  label: String
});

// 尺寸映射 (点的大小)
const sizeConfig = {
  sm: 'h-2 w-2',
  md: 'h-3 w-3',
  lg: 'h-4 w-4'
};

// 尺寸映射 (文字大小)
const textSizeConfig = {
  sm: 'text-[10px]',
  md: 'text-xs',
  lg: 'text-sm'
};

// 状态样式映射 (背景、阴影、文字色)
const statusColors: Record<StatusType, { bg: string; shadow: string; text: string }> = {
  running: {
    bg: 'bg-cyan-400', 
    shadow: 'shadow-glow-cyan', // 使用 Theme 定义的变量
    text: 'text-cyan-400'
  },
  success: {
    bg: 'bg-emerald-400',
    shadow: 'shadow-glow-green',
    text: 'text-emerald-400'
  },
  error: {
    bg: 'bg-red-500',
    shadow: 'shadow-glow-red',
    text: 'text-red-400'
  },
  pending: {
    bg: 'bg-amber-400',
    shadow: 'shadow-[0_0_15px_rgba(251,191,36,0.4)]', // 自定义琥珀色发光
    text: 'text-amber-400'
  },
  idle: {
    bg: 'bg-gray-600',
    shadow: 'shadow-none',
    text: 'text-gray-500'
  }
};

// 简单的文案处理 (首字母大写等)
const statusLabel = computed(() => {
  if (props.label) return props.label;
  return props.status.toUpperCase(); // HUD 风格通常全大写
});
</script>