<template>
  <div class="h-full flex flex-col">
    <!-- 顶部：全局搜索/项目切换 -->
    <div class="mb-4">
      <div class="hud-input flex items-center gap-2 p-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input 
          type="text" 
          placeholder="Search tasks..." 
          class="bg-transparent border-none outline-none text-sm flex-grow"
        />
      </div>
    </div>

    <!-- 中部：垂直任务列表 -->
    <div class="flex-grow overflow-y-auto pr-2">
      <h3 class="text-xs font-semibold text-gray-500 uppercase mb-2">Active Tasks</h3>
      
      <div 
        v-for="task in tasks" 
        :key="task.id" 
        class="task-item"
      >
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-gray-100">{{ task.name }}</span>
          <StatusDot :status="task.status" />
        </div>
        <div class="text-xs text-gray-400 truncate">{{ task.description }}</div>
      </div>

      <h3 class="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Completed</h3>
      <div 
        v-for="task in completedTasks" 
        :key="task.id" 
        class="task-item"
      >
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-gray-400">{{ task.name }}</span>
          <StatusDot :status="task.status" />
        </div>
        <div class="text-xs text-gray-500 truncate">{{ task.description }}</div>
      </div>
    </div>

    <!-- 底部：用户设置/系统状态 -->
    <div class="mt-4 pt-4 border-t border-white/10">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-gradient-to-br from-sci-blue to-sci-green flex items-center justify-center">
          <span class="text-xs font-medium">U</span>
        </div>
        <div class="flex-grow">
          <div class="text-sm font-medium">User</div>
          <div class="text-xs text-gray-400">System Status: Online</div>
        </div>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import StatusDot from '@/components/ui/StatusDot.vue';

interface Task {
  id: string;
  name: string;
  description: string;
  status: 'idle' | 'running' | 'success' | 'error';
}

const tasks = ref<Task[]>([
  {
    id: 'task-001',
    name: 'Data Pipeline',
    description: 'ETL process for customer data',
    status: 'running',
  },
  {
    id: 'task-002',
    name: 'Model Training',
    description: 'Train regression model on sales data',
    status: 'idle',
  },
  {
    id: 'task-003',
    name: 'Report Generation',
    description: 'Generate weekly performance reports',
    status: 'idle',
  },
]);

const completedTasks = ref<Task[]>([
  {
    id: 'task-004',
    name: 'Data Backup',
    description: 'Backup all database tables',
    status: 'success',
  },
]);
</script>
