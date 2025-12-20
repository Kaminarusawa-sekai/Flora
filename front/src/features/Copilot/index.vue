<template>
  <div class="h-full flex flex-col">
    <!-- 顶部：当前关联的 Task ID -->
    <div class="p-3 border-b border-white/10">
      <div class="text-xs text-gray-500">Current Task ID</div>
      <div class="text-sm font-mono text-sci-blue">task-002</div>
    </div>

    <!-- 中部：对话消息列表 -->
    <div class="flex-grow overflow-y-auto p-3">
      <!-- AI 消息 -->
      <div class="mb-4">
        <div class="flex items-start gap-2">
          <div class="w-6 h-6 rounded-full bg-gradient-to-br from-sci-blue to-sci-green flex items-center justify-center flex-shrink-0">
            <span class="text-xs font-medium">AI</span>
          </div>
          <div class="bg-white/2 rounded-xl p-3 max-w-[85%]">
            <p class="text-sm text-gray-100">I've analyzed the pipeline. The data processing step is currently running. Would you like me to explain the current status or execute any commands?</p>
            <div class="mt-2 text-xs text-gray-400">Just now</div>
          </div>
        </div>
      </div>

      <!-- 用户消息 -->
      <div class="mb-4 flex justify-end">
        <div class="flex items-start gap-2 flex-row-reverse">
          <div class="w-6 h-6 rounded-full bg-gradient-to-br from-sci-green to-sci-blue flex items-center justify-center flex-shrink-0">
            <span class="text-xs font-medium">U</span>
          </div>
          <div class="bg-white/3 rounded-xl p-3 max-w-[85%]">
            <p class="text-sm text-gray-100">Show me the details of the running task</p>
            <div class="mt-2 text-xs text-gray-400">Just now</div>
          </div>
        </div>
      </div>

      <!-- AI 消息，包含代码块 -->
      <div class="mb-4">
        <div class="flex items-start gap-2">
          <div class="w-6 h-6 rounded-full bg-gradient-to-br from-sci-blue to-sci-green flex items-center justify-center flex-shrink-0">
            <span class="text-xs font-medium">AI</span>
          </div>
          <div class="bg-white/2 rounded-xl p-3 max-w-[85%]">
            <p class="text-sm text-gray-100 mb-2">Here's the current status of <code class="text-sci-blue font-mono text-xs">task-002</code>:</p>
            <div class="bg-white/5 rounded-lg p-2 overflow-x-auto">
              <pre class="text-xs font-mono text-gray-300">{
  "id": "task-002",
  "name": "Data Processing",
  "status": "running",
  "progress": 45,
  "start_time": "2025-12-20T02:30:00Z",
  "estimated_completion": "2025-12-20T02:45:00Z"
}</pre>
            </div>
            <div class="mt-2 text-xs text-gray-400">Just now</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：HUD 风格输入框 -->
    <div class="p-3 border-t border-white/10">
      <InputHud 
        v-model="message" 
        placeholder="Type a message or /command..." 
        @enter="sendMessage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import InputHud from '@/components/ui/InputHud.vue';

const message = ref('');

const sendMessage = () => {
  if (message.value.trim()) {
    // 发送消息逻辑
    console.log('Sending message:', message.value);
    message.value = '';
  }
};
</script>
