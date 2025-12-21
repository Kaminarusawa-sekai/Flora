<template>
  <div
    class="relative overflow-hidden glass-panel group transition-all duration-300"
    :class="[
      hoverable ? 'glass-hover cursor-pointer' : '',
      noPadding ? 'p-0' : 'p-5'
    ]"
  >
    <div
      class="absolute inset-x-0 top-0 h-[1px] w-full z-20 pointer-events-none 
             bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent 
             opacity-50 transition-opacity duration-300"
      :class="{ 'group-hover:opacity-100 group-hover:via-cyan-300/60': hoverable }"
    ></div>

    <div class="absolute inset-x-0 bottom-0 h-[1px] w-full z-20 pointer-events-none bg-gradient-to-r from-transparent via-blue-500/10 to-transparent opacity-30"></div>
    
    <div class="relative z-10 h-full">
      <slot></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
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
</script>

<style scoped>
/* 确保 Safari 下的模糊性能 */
div {
  transform: translateZ(0);
}
</style>
