<template>
  <div class="flex h-screen w-screen text-gray-200 overflow-hidden font-sans selection:bg-sci-blue/30 relative">
    <!-- 区域 A: 任务导航栏 -->
    <aside class="h-full flex-shrink-0 py-4 pl-4 z-30">
       <slot name="nav"></slot>
    </aside>
    <!-- 区域 B: 对话栏 -->
    <transition name="slide-fade">
      <aside v-if="$slots.sidebar" class="
        h-full flex-shrink-0 py-4 pl-4 z-20
        transition-all duration-300 ease-in-out
      ">
        <slot name="sidebar"></slot>
      </aside>
    </transition>
     <!-- 区域 B: 智能对话流 -->
    <transition name="slide-fade">
      <section class="
        h-full flex-shrink-0 p-4 pl-0 z-20 
        transition-all duration-300 ease-in-out
      ">
        <slot name="chat"></slot>
      </section>
    </transition>
     <!-- 区域 C: DAG 执行画布 -->
    <main class="flex-grow relative z-10 py-4">
      <slot name="canvas"></slot>
    </main>
    <!-- 区域 D: 资源与控制 -->
    <transition name="slide-fade">
      <aside class="
        h-full flex-shrink-0 p-4 z-20
        transition-all duration-300 ease-in-out
      ">
        <slot name="resources"></slot>
      </aside>
    </transition>

  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
/* 保持原有动画样式 */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all 0.4s cubic-bezier(0.25, 1, 0.5, 1);
}
.slide-fade-enter-from, .slide-fade-leave-to {
  transform: translateX(-20px);
  opacity: 0;
  width: 0;
  padding-left: 0; /* 动画时移除左边距，防止跳动 */
  margin: 0;
}
</style>
