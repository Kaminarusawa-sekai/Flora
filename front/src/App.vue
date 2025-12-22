<script setup lang="ts">
import { ref } from 'vue';
import MainLayout from '@/layouts/MainLayout.vue';
import GlassCard from '@/components/ui/GlassCard.vue';
import TaskSidebar from '@/features/TaskSidebar/index.vue';
import Copilot from '@/features/Copilot/index.vue';
import DagEditor from '@/features/DagEditor/index.vue';
import ResourcePanel from '@/features/ResourcePanel/index.vue';

// 当前选中的任务ID
const selectedTaskId = ref('TSK-01');

// 处理任务切换
const handleTaskSelect = (taskId: string) => {
  selectedTaskId.value = taskId;
};
</script>

<template>

  <MainLayout>
    <template #sidebar>
      <GlassCard class="h-full">
        <TaskSidebar @task-select="handleTaskSelect" />
      </GlassCard>
    </template>

    <template #chat>
      <GlassCard class="h-full bg-white/2">
        <Copilot :selected-task-id="selectedTaskId" />
      </GlassCard>
    </template>

    <template #canvas>
      <DagEditor />
    </template>

    <template #resources>
      <GlassCard class="h-full">
        <ResourcePanel />
      </GlassCard>
    </template>
  </MainLayout>
</template>

<style scoped>
/* 全局样式已在 main.css 中定义 */
</style>
