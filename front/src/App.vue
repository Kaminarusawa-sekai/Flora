<script setup lang="ts">
import { ref } from 'vue';
import MainLayout from '@/layouts/MainLayout.vue';
import GlassCard from '@/components/ui/GlassCard.vue';
import TaskSidebar from '@/features/TaskSidebar/index.vue';
import NavigationPanel from '@/features/NavigationPanel/index.vue';
import Copilot from '@/features/Copilot/index.vue';
import DagEditor from '@/features/DagEditor/index.vue';
import TreeEditor from '@/features/TreeEditor/index.vue';
import ResourcePanel from '@/features/ResourcePanel/index.vue';
import MarkdownViewer from '@/features/MarkdownViewer/index.vue';

// 当前选中的任务ID
const selectedTaskId = ref('TSK-01');
// 当前激活的视图
const activeView = ref('tasks');

// 处理任务切换
const handleTaskSelect = (taskId: string) => {
  selectedTaskId.value = taskId;
};

// 处理导航切换
const handleNavChange = (view: string) => {
  activeView.value = view;
};
</script>

<template>

  <MainLayout>
    <template #nav>
      <GlassCard class="h-full" noPadding>
        <NavigationPanel @nav-change="handleNavChange" />
      </GlassCard>
    </template>

    <template #sidebar v-if="activeView === 'tasks'">
      <GlassCard class="h-full w-[380px]"> 
        <TaskSidebar @task-select="handleTaskSelect" />
      </GlassCard>
    </template>

    <template #chat>
      <!-- 仅在tasks视图显示Copilot组件 -->
      <GlassCard v-if="activeView === 'tasks'" class="h-full  w-[400px] bg-white/2">
        <Copilot :selected-task-id="selectedTaskId" />
      </GlassCard>
    </template>

    <template #canvas>
      <!-- tasks视图显示DagEditor组件 -->
      <DagEditor v-if="activeView === 'tasks'" :selected-task-id="selectedTaskId" />
      <!-- overview视图显示TreeEditor组件 -->
      <TreeEditor v-else-if="activeView === 'overview'" />
      <!-- search视图显示markdown文档 -->
      <GlassCard v-else-if="activeView === 'search'" class="h-full bg-white/2">
        <MarkdownViewer />
      </GlassCard>
      <!-- 其他视图下显示提示信息 -->
      <div v-else class="h-full flex items-center justify-center text-gray-400">
        <div class="text-center">
          <h2 class="text-2xl font-bold mb-2">{{ activeView.charAt(0).toUpperCase() + activeView.slice(1) }}</h2>
          <p>该视图正在开发中...</p>
        </div>
      </div>
    </template>

    <template #resources>
      <!-- 仅在tasks视图显示ResourcePanel组件 -->
      <GlassCard v-if="activeView === 'tasks'" class="h-full">
        <ResourcePanel />
      </GlassCard>
    </template>
  </MainLayout>
</template>

<style scoped>
/* 全局样式已在 main.css 中定义 */
</style>
