<template>
  <div class="h-full flex flex-col">
    <!-- 顶部：标签切换 -->
    <div class="p-3 border-b border-white/10">
      <div class="flex gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="
            px-3 py-1 rounded-xl text-sm font-medium
            transition-all duration-300
            flex-grow text-center
          "
          :class="{
            'bg-sci-blue/20 text-sci-blue border border-sci-blue/30': activeTab === tab.id,
            'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10 hover:text-gray-300': activeTab !== tab.id,
          }"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 中部：标签内容 -->
    <div class="flex-grow overflow-y-auto p-3">
      <!-- 文件库 -->
      <div v-if="activeTab === 'assets'" class="space-y-4">
        <h3 class="text-xs font-semibold text-gray-500 uppercase">File Library</h3>
        
        <!-- 文件树 -->
        <div class="space-y-2">
          <!-- 目录项 -->
          <div class="space-y-1">
            <div class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
              <span>data</span>
            </div>
            <!-- 文件项 -->
            <div class="ml-6 space-y-1">
              <div class="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-gray-200">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>dataset.csv</span>
                <span class="text-xs text-gray-500 ml-auto">2.3 MB</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-gray-200">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>metadata.json</span>
                <span class="text-xs text-gray-500 ml-auto">1.2 KB</span>
              </div>
            </div>
          </div>

          <!-- 目录项 -->
          <div class="space-y-1">
            <div class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
              </svg>
              <span>models</span>
            </div>
            <!-- 文件项 -->
            <div class="ml-6 space-y-1">
              <div class="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-gray-200">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>model-v1.pth</span>
                <span class="text-xs text-gray-500 ml-auto">128 MB</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 待办/参数 -->
      <div v-else-if="activeTab === 'pending'" class="space-y-4">
        <h3 class="text-xs font-semibold text-gray-500 uppercase">Pending Parameters</h3>
        
        <!-- 参数表单 -->
        <div class="space-y-4">
          <div>
            <label class="block text-xs text-gray-400 mb-1">Batch Size</label>
            <input 
              type="number" 
              class="w-full hud-input" 
              placeholder="Enter batch size"
              value="32"
            />
          </div>
          
          <div>
            <label class="block text-xs text-gray-400 mb-1">Learning Rate</label>
            <input 
              type="number" 
              step="0.0001" 
              class="w-full hud-input" 
              placeholder="Enter learning rate"
              value="0.001"
            />
          </div>
          
          <div>
            <label class="block text-xs text-gray-400 mb-1">Epoch Count</label>
            <input 
              type="number" 
              class="w-full hud-input" 
              placeholder="Enter epoch count"
              value="100"
            />
          </div>

          <h3 class="text-xs font-semibold text-gray-500 uppercase mt-6 mb-2">Task Checklist</h3>
          
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <input type="checkbox" id="check1" class="w-4 h-4 rounded bg-white/10 border-white/20 text-sci-blue focus:ring-0" checked />
              <label for="check1" class="text-sm text-gray-300">Data validation complete</label>
            </div>
            <div class="flex items-center gap-2">
              <input type="checkbox" id="check2" class="w-4 h-4 rounded bg-white/10 border-white/20 text-sci-blue focus:ring-0" checked />
              <label for="check2" class="text-sm text-gray-300">Model architecture defined</label>
            </div>
            <div class="flex items-center gap-2">
              <input type="checkbox" id="check3" class="w-4 h-4 rounded bg-white/10 border-white/20 text-sci-blue focus:ring-0" />
              <label for="check3" class="text-sm text-gray-300">Hyperparameters tuned</label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：操作按钮 -->
    <div class="mt-3 p-3 border-t border-white/10">
      <GlowButton class="w-full">
        Save Changes
      </GlowButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import GlowButton from '@/components/ui/GlowButton.vue';

interface Tab {
  id: string;
  label: string;
}

const tabs = ref<Tab[]>([
  { id: 'assets', label: 'Files' },
  { id: 'pending', label: 'Params' },
]);

const activeTab = ref('assets');
</script>
