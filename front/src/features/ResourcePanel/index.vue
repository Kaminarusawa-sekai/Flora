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

    <div v-if="activeTab === 'files'" class="flex items-center justify-between mb-2">
      <div class="text-xs text-gray-400">
        {{ isLoading ? 'Loading...' : 'Files' }}
      </div>
      <div class="flex items-center gap-2">
        <span v-if="errorMessage" class="text-[10px] text-red-400">{{ errorMessage }}</span>
        <GlowButton variant="ghost" size="sm" @click="triggerUpload">
          Upload
        </GlowButton>
        <input ref="fileInputRef" type="file" class="hidden" @change="handleUpload" />
      </div>
    </div>

    <div v-if="activeTab === 'memory'" class="flex items-center justify-between mb-2">
      <div class="text-xs text-gray-400">
        {{ isLoading ? 'Loading...' : 'Memories' }}
      </div>
      <div class="flex items-center gap-2">
        <span v-if="errorMessage" class="text-[10px] text-red-400">{{ errorMessage }}</span>
      </div>
    </div>

    <div class="space-y-2">
      <!-- Files Tab Content -->
      <div 
        v-if="activeTab === 'files'"
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

      <!-- Memory Tab Content -->
      <div 
        v-if="activeTab === 'memory'"
        v-for="memory in memories" 
        :key="memory.id" 
        class="flex items-start p-2 rounded-lg hover:bg-white/5 transition group cursor-pointer border border-transparent hover:border-white/5"
      >
        <svg class="w-5 h-5 text-sci-green opacity-70 mr-3 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <div class="flex-grow">
          <div class="text-xs text-gray-300 group-hover:text-white font-medium">{{ memory.key }}</div>
          <div class="text-[10px] text-gray-600 whitespace-pre-wrap">{{ memory.value }}</div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="activeTab === 'memory' && memories.length === 0 && !isLoading" class="text-center py-4 text-xs text-gray-500">
        No memories found
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
import { ref, onMounted, watch } from 'vue';
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

// 记忆类型定义
interface Memory {
  id: string;
  key: string;
  value: string;
}

// 导入 API
import RAGAPI from '@/api/rag';

// 状态管理
const tabs = ref<Tab[]>([
  { id: 'files', label: 'Files' },
  { id: 'memory', label: 'Memory' },
  { id: 'logs', label: 'Logs' }
]);

const activeTab = ref('files');
const memoryUsage = ref(42);
const isLoading = ref(false);
const errorMessage = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);

const files = ref<File[]>([]);
const memories = ref<Memory[]>([]);
const currentUserId = ref('1'); // 这里可以根据实际情况获取用户ID

// 事件处理
const selectFile = (file: File) => {
  console.log('Selected file:', file);
  // 这里可以添加文件选择逻辑
};

const formatFileSize = (value: number | string | undefined) => {
  const numeric = typeof value === 'string' ? Number(value) : value;
  if (!numeric && numeric !== 0) return '-';
  if (Number.isNaN(numeric)) return '-';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = numeric;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)}${units[unitIndex]}`;
};

const formatDateTime = (value: string | number | undefined) => {
  if (!value) return '-';
  const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
};

const normalizeDocuments = (payload: any): File[] => {
  const docs = payload?.documents || payload?.data || payload?.items || [];
  if (!Array.isArray(docs)) return [];
  return docs.map((doc: any, index: number) => ({
    id: doc?.id || doc?.document_id || doc?.uuid || `doc-${index}`,
    name: doc?.name || doc?.title || doc?.filename || 'Untitled',
    size: formatFileSize(doc?.size || doc?.file_size || doc?.size_in_bytes),
    updated: formatDateTime(doc?.updated_at || doc?.updated || doc?.created_at),
  }));
};

const fetchFiles = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const data = await RAGAPI.getFiles();
    files.value = normalizeDocuments(data);
  } catch (error: any) {
    errorMessage.value = error?.message || 'Load failed';
    files.value = [];
  } finally {
    isLoading.value = false;
  }
};

const fetchMemories = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  try {
    const data = await RAGAPI.getCoreMemories(currentUserId.value);
    memories.value = Array.isArray(data) ? data : [];
  } catch (error: any) {
    errorMessage.value = error?.message || 'Load memories failed';
    memories.value = [];
  } finally {
    isLoading.value = false;
  }
};

const triggerUpload = () => {
  fileInputRef.value?.click();
};

const handleUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  isLoading.value = true;
  errorMessage.value = '';
  try {
    await RAGAPI.uploadFile(file);
    await fetchFiles();
  } catch (error: any) {
    errorMessage.value = error?.message || 'Upload failed';
  } finally {
    isLoading.value = false;
    if (target) target.value = '';
  }
};

const deployChanges = () => {
  console.log('Deploying changes...');
  // 这里可以添加部署逻辑
};

const exportLogs = () => {
  console.log('Exporting logs...');
  // 这里可以添加导出日志逻辑
};

// 监听标签变化，自动加载对应数据
watch(activeTab, (newTab) => {
  if (newTab === 'files') {
    fetchFiles();
  } else if (newTab === 'memory') {
    fetchMemories();
  }
});

onMounted(() => {
  if (activeTab.value === 'files') {
    fetchFiles();
  } else if (activeTab.value === 'memory') {
    fetchMemories();
  }
});
</script>
