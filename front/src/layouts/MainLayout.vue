<template>
  <div class="flex h-screen w-screen text-gray-200 overflow-hidden font-sans selection:bg-sci-blue/30 relative">
    
    <!-- 区域 A: 任务导航栏 -->
    <aside class="
      w-[460px] h-full flex-shrink-0 p-4 z-20
      transition-all duration-300 ease-in-out
    ">
      <slot name="sidebar"></slot>
    </aside>

    <!-- 区域 B: 智能对话流 -->
    <transition name="slide-fade">
      <section v-if="!appStore.isChatCollapsed" class="
        w-[440px] h-full flex-shrink-0 p-4 pl-0 z-20
        transition-all duration-300 ease-in-out
      ">
        <slot name="chat"></slot>
      </section>
    </transition>

    <!-- 区域 C: DAG 执行画布 -->
    <main class="flex-grow relative z-10">
      <slot name="canvas"></slot>
    </main>

    <!-- 区域 D: 资源与控制 -->
    <aside class="
      w-[300px] h-full flex-shrink-0 p-4 z-20
      transition-all duration-300 ease-in-out
    ">
      <slot name="resources"></slot>
    </aside>

  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/useAppStore';

const appStore = useAppStore();
</script>

<style scoped>
/* 简单的进入/离开动画 */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}
.slide-fade-enter-from, .slide-fade-leave-to {
  transform: translateX(-20px);
  opacity: 0;
  width: 0;
  padding: 0; /* 防止边距导致动画跳动 */
}
</style>
