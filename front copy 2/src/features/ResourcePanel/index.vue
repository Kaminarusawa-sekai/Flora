<template>
  <GlassCard class="h-full">
    <template #header>
      <div class="flex p-1 bg-black/20 rounded-xl mb-4 border border-white/5">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          class="flex-1 py-1.5 text-xs font-medium rounded-lg transition"
          :class="{
            'bg-white/10 text-white shadow-sm': activeTab === tab.id,
            'text-gray-500 hover:text-gray-300': activeTab !== tab.id
          }"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>
    </template>

    <div class="space-y-2">
      <div 
        v-for="file in files" 
        :key="file.id" 
        class="flex items-center p-2 rounded-lg hover:bg-white/5 transition group cursor-pointer border border-transparent hover:border-white/5"
        @click="selectFile(file)"
      >
        <svg class="w-5 h-5 text-sci-blue opacity-70 mr-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
        <div class="flex-grow">
          <div class="text-xs text-gray-300 group-hover:text-white">{{ file.name }}</div>
          <div class="text-[10px] text-gray-600 font-mono">{{ file.size }} • {{ file.updated }}</div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="pt-4 border-t border-white/5 space-y-3">
        <div class="flex justify-between text-xs text-gray-400 mb-2">
          <span>Memory Usage</span>
          <span class="text-sci-blue">{{ memoryUsage }}%</span>
        </div>
        <div class="h-1 w-full bg-gray-800 rounded-full overflow-hidden mb-4">
          <div class="h-full bg-sci-blue w-[42%] shadow-[0_0_10px_#3b82f6] transition-all duration-500"></div>
        </div>

        <GlowButton variant="primary" class="w-full shadow-lg" @click="deployChanges">
          Deploy Changes
        </GlowButton>
        
        <GlowButton variant="ghost" size="sm" class="w-full" @click="exportLogs">
          Export Logs
        </GlowButton>
      </div>
    </template>
  </GlassCard>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import GlassCard from '@/components/ui/GlassCard.vue';
import GlowButton from '@/components/ui/GlowButton.vue';

// 标签类型定义
interface Tab {
  id: string;
  label: string;
}

// 文件类型定义
interface File {
  id: string;
  name: string;
  size: string;
  updated: string;
}

// 状态管理
const tabs = ref<Tab[]>([
  { id: 'files', label: 'Files' },
  { id: 'params', label: 'Params' },
  { id: 'logs', label: 'Logs' }
]);

const activeTab = ref('files');
const memoryUsage = ref(42);

// 数据模拟
const files = ref<File[]>([
  { id: 'file-1', name: 'dataset_v1.csv', size: '24MB', updated: 'Just now' },
  { id: 'file-2', name: 'dataset_v2.csv', size: '32MB', updated: '5m ago' },
  { id: 'file-3', name: 'model_weights.pth', size: '1.2GB', updated: '1h ago' },
  { id: 'file-4', name: 'config.json', size: '12KB', updated: '2h ago' },
  { id: 'file-5', name: 'training_logs.txt', size: '8MB', updated: 'Yesterday' }
]);

// 事件处理
const selectFile = (file: File) => {
  console.log('Selected file:', file);
  // 这里可以添加文件选择逻辑
};

const deployChanges = () => {
  console.log('Deploying changes...');
  // 这里可以添加部署逻辑
};

const exportLogs = () => {
  console.log('Exporting logs...');
  // 这里可以添加导出日志逻辑
};
</script>