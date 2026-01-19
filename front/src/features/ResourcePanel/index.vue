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
        <GlowButton variant="ghost" size="sm" @click="openAddMemoryModal">
          + Add
        </GlowButton>
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
        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
          <button
            class="p-1 rounded hover:bg-white/10 text-gray-400 hover:text-white"
            @click.stop="openEditMemoryModal(memory)"
            title="Edit"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
          <button
            class="p-1 rounded hover:bg-white/10 text-gray-400 hover:text-red-400"
            @click.stop="confirmDeleteMemory(memory)"
            title="Delete"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
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

  <!-- Memory Edit/Add Modal -->
  <Teleport to="body">
    <div v-if="showMemoryModal" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeMemoryModal"></div>
      <div class="relative bg-gray-900 border border-white/10 rounded-xl p-6 w-[400px] shadow-2xl">
        <h3 class="text-sm font-medium text-white mb-4">
          {{ isEditMode ? 'Edit Memory' : 'Add Memory' }}
        </h3>
        <div class="space-y-4">
          <div>
            <label class="block text-xs text-gray-400 mb-1">Key</label>
            <input
              v-model="memoryForm.key"
              type="text"
              :disabled="isEditMode"
              class="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-sci-blue disabled:opacity-50"
              placeholder="e.g., 姓名, 部门, 电话"
            />
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1">Value</label>
            <textarea
              v-model="memoryForm.value"
              rows="3"
              class="w-full px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-sci-blue resize-none"
              placeholder="Memory content..."
            ></textarea>
          </div>
        </div>
        <div class="flex justify-end gap-2 mt-6">
          <GlowButton variant="ghost" size="sm" @click="closeMemoryModal">
            Cancel
          </GlowButton>
          <GlowButton variant="primary" size="sm" @click="saveMemory" :disabled="!memoryForm.key || !memoryForm.value">
            {{ isEditMode ? 'Save' : 'Add' }}
          </GlowButton>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Delete Confirmation Modal -->
  <Teleport to="body">
    <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeDeleteConfirm"></div>
      <div class="relative bg-gray-900 border border-white/10 rounded-xl p-6 w-[350px] shadow-2xl">
        <h3 class="text-sm font-medium text-white mb-2">Delete Memory</h3>
        <p class="text-xs text-gray-400 mb-4">
          Are you sure you want to delete "{{ memoryToDelete?.key }}"? This action cannot be undone.
        </p>
        <div class="flex justify-end gap-2">
          <GlowButton variant="ghost" size="sm" @click="closeDeleteConfirm">
            Cancel
          </GlowButton>
          <GlowButton variant="primary" size="sm" class="!bg-red-600 hover:!bg-red-500" @click="deleteMemory">
            Delete
          </GlowButton>
        </div>
      </div>
    </div>
  </Teleport>
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
const currentUserId = ref(localStorage.getItem('userId') || '<user_id:1,tenant_id:1>'); // 从 localStorage 获取用户ID

// Memory Modal 状态
const showMemoryModal = ref(false);
const isEditMode = ref(false);
const memoryForm = ref({ key: '', value: '' });
const showDeleteConfirm = ref(false);
const memoryToDelete = ref<Memory | null>(null);

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

// Memory CRUD 操作
const openAddMemoryModal = () => {
  isEditMode.value = false;
  memoryForm.value = { key: '', value: '' };
  showMemoryModal.value = true;
};

const openEditMemoryModal = (memory: Memory) => {
  isEditMode.value = true;
  memoryForm.value = { key: memory.key, value: memory.value };
  showMemoryModal.value = true;
};

const closeMemoryModal = () => {
  showMemoryModal.value = false;
  memoryForm.value = { key: '', value: '' };
};

const saveMemory = async () => {
  if (!memoryForm.value.key || !memoryForm.value.value) return;

  isLoading.value = true;
  errorMessage.value = '';
  try {
    await RAGAPI.setCoreMemory(currentUserId.value, memoryForm.value.key, memoryForm.value.value);
    closeMemoryModal();
    await fetchMemories();
  } catch (error: any) {
    errorMessage.value = error?.message || 'Save memory failed';
  } finally {
    isLoading.value = false;
  }
};

const confirmDeleteMemory = (memory: Memory) => {
  memoryToDelete.value = memory;
  showDeleteConfirm.value = true;
};

const closeDeleteConfirm = () => {
  showDeleteConfirm.value = false;
  memoryToDelete.value = null;
};

const deleteMemory = async () => {
  if (!memoryToDelete.value) return;

  isLoading.value = true;
  errorMessage.value = '';
  try {
    await RAGAPI.deleteCoreMemory(currentUserId.value, memoryToDelete.value.key);
    closeDeleteConfirm();
    await fetchMemories();
  } catch (error: any) {
    errorMessage.value = error?.message || 'Delete memory failed';
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
