<template>
  <div
    class="relative overflow-hidden glass-panel group transition-all duration-300 flex flex-col h-full"
    :class="[
      hoverable ? 'glass-hover cursor-pointer' : '',
      // 注意：这里移除了 p-5，将内边距控制权下放给各个区域
      noPadding ? '' : ''
    ]"
  >
    <div
      class="absolute inset-x-0 top-0 h-[1px] w-full z-20 pointer-events-none 
             bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent 
             opacity-50 transition-opacity duration-300"
      :class="{ 'group-hover:opacity-100 group-hover:via-cyan-300/60': hoverable }"
    ></div>
    <div class="absolute inset-x-0 bottom-0 h-[1px] w-full z-20 pointer-events-none bg-gradient-to-r from-transparent via-blue-500/10 to-transparent opacity-30"></div>

    <div v-if="$slots.header" class="relative z-20 flex-shrink-0" :class="noPadding ? '' : 'p-5 pb-2'">
      <slot name="header"></slot>
    </div>

    <div
      class="relative z-10 flex-1 overflow-y-auto custom-scrollbar min-h-0"
      :class="noPadding ? '' : 'px-5'"
    >
      <slot></slot>
    </div>

    <div v-if="$slots.footer" class="relative z-20 flex-shrink-0" :class="noPadding ? '' : 'p-5 pt-2'">
      <slot name="footer"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSlots } from 'vue'

defineProps({
  // 是否开启悬浮高亮效果（用于可交互卡片）
  hoverable: {
    type: Boolean,
    default: false
  },
  // 是否移除默认内边距（用于需要内容贴边的场景）
  noPadding: {
    type: Boolean,
    default: false
  }
});

const $slots = useSlots();
</script>

<style scoped>
/* 确保 Safari 下的模糊性能 */
div {
  transform: translateZ(0);
}

/* --- 滚动条美化 (针对 Webkit 内核) --- */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px; /* 滚动条宽度 */
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent; /* 轨道透明 */
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.1); /* 滑块半透明白色 */
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.2); /* 悬停加深 */
}
</style>
