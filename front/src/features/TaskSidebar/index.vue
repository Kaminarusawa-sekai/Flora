<template>
  <!-- Main Task Content -->
  <GlassCard class="h-full relative">
    <template #header>
      <div class="mb-6 relative">
        <h2 class="text-xs font-mono text-gray-500 mb-2 uppercase tracking-[0.2em]">Mission Control</h2>
        <div class="relative">
          <InputHud
            v-model="searchQuery"
            placeholder="SEARCH TARGET..."
          >
            <template #prefix>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </template>
          </InputHud>
        </div>
        
        <!-- 新增对话按钮 -->
        <div class="mt-4">
          <GlowButton
            variant="primary"
            size="md"
            @click="createNewConversation"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            NEW CONVERSATION
          </GlowButton>
        </div>
      </div>
    </template>

    <div class="py-2 space-y-6">
      <h3 class="text-xs font-semibold text-gray-500 uppercase mb-3 flex items-center gap-2">
        <span class="w-2 h-2 bg-sci-blue rounded-full"></span>
        ACTIVE TASKS
      </h3>
     
      <GlassCard
        v-for="task in filteredTasks"
        :key="task.id"
        hoverable
        noPadding
        class="group cursor-pointer transition-all duration-300 mb-4"
        :class="task.active ? 'border-sci-blue/50 bg-sci-blue/10 shadow-xl shadow-sci-blue/40 ring-1 ring-sci-blue/50' : ''"
        @click="activateTask(task.id)"
      >
        <div class="p-5 flex items-center gap-4">
          <StatusDot :status="task.status" />
         
          <div class="flex-grow">
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">{{ task.name }}</span>
              <span class="text-[10px] font-mono text-gray-600 group-hover:text-sci-blue">{{ task.id.substring(0, 5) }}..</span>
            </div>
            <p class="text-xs text-gray-500 line-clamp-1">{{ task.description }}</p>
          </div>
        </div>
      </GlassCard>

      <h3 class="text-xs font-semibold text-gray-500 uppercase mt-6 mb-3 flex items-center gap-2">
        <span class="w-2 h-2 bg-sci-green rounded-full"></span>
        COMPLETED
      </h3>
     
      <GlassCard
        v-for="task in filteredCompletedTasks"
        :key="task.id"
        hoverable
        noPadding
        class="group cursor-pointer transition-all duration-300 opacity-70 hover:opacity-100 mb-4"
        :class="task.active ? 'border-sci-blue/50 bg-sci-blue/10 shadow-xl shadow-sci-blue/40 ring-1 ring-sci-blue/50' : ''"
        @click="activateTask(task.id)"
      >
        <div class="p-5 flex items-center gap-4">
          <StatusDot :status="task.status" />
         
          <div class="flex-grow">
            <div class="flex justify-between items-center mb-1">
              <span class="text-sm font-medium text-gray-400 group-hover:text-gray-300 transition-colors">{{ task.name }}</span>
              <span class="text-[10px] font-mono text-gray-600 group-hover:text-sci-blue">{{ task.id.substring(0, 5) }}..</span>
            </div>
            <p class="text-xs text-gray-500 line-clamp-1">{{ task.description }}</p>
          </div>
        </div>
      </GlassCard>
    </div>

    <template #footer>
      <div class="pt-4 border-t border-white/5 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <StatusDot status="running" size="sm" />
          <span class="text-xs font-mono text-sci-green">SYSTEM ONLINE</span>
        </div>
        <button class="text-gray-500 hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
        </button>
      </div>
    </template>
  </GlassCard>
</template>



<script setup lang="ts">

import { ref, computed, onMounted } from 'vue';
// @ts-ignore - JavaScript module with no type declarations
import { getLatestTraceByRequest, getTaskDetail } from '@/api/order';
// @ts-ignore - JavaScript module with no type declarations
import ConversationAPI from '@/api/conversation';

import GlassCard from '@/components/ui/GlassCard.vue';

import StatusDot from '@/components/ui/StatusDot.vue';

import InputHud from '@/components/ui/InputHud.vue';

import GlowButton from '@/components/ui/GlowButton.vue';



const searchQuery = ref('');

const activeNavItem = ref('tasks');



interface Task {

  id: string;

  name: string;

  description: string;

  status: 'idle' | 'running' | 'success' | 'error' | 'pending';

  active?: boolean;

}



const tasks = ref<Task[]>([]);
const completedTasks = ref<Task[]>([]);

// 从API获取任务数据
const fetchTasksFromApi = async () => {
  try {
    // 从localStorage获取userId，不存在则使用默认值1
    const userId = localStorage.getItem('userId') || '<user_id:1,tenant_id:1>';

    
    

    // 获取用户所有活跃会话
    const sessions = await ConversationAPI.getUserSessions(userId);
    if (!sessions || sessions.length === 0) {
      console.warn('No active sessions found for user:', userId);
      return;
    }

    // 遍历每个会话，获取对应的任务数据
    const activeTasks: Task[] = [];
    const completedTasksList: Task[] = [];

    for (const sessionData of sessions) {
      // 先创建一个基本的任务对象
      let processedTask: Task = {
        id: sessionData.session_id || 'unknown',
        name: sessionData.name || '未命名对话',
        description: sessionData.description || 'No description available',
        status: 'pending',
        active: false
      };

      // 尝试获取更详细的任务信息
      try {
        // 检查是否有request_id
        if (sessionData.request_id) {
          // 使用request_id获取latest_trace_id
          const traceResponse = await getLatestTraceByRequest(sessionData.request_id);
          const traceId = traceResponse.latest_trace_id;

          if (traceId) {
            // 更新任务id为trace_id
            processedTask.id = traceId;
            
            try {
              // 使用trace_id获取任务详情
              const taskDetail = await getTaskDetail(traceId);
              if (taskDetail) {
                // 更新任务状态
                processedTask.status = taskDetail.status || 'pending';
              }
            } catch (error) {
              console.error('Error getting task detail for trace_id:', traceId, error);
              // 继续执行，使用默认状态
            }
          }
        }
      } catch (error) {
        console.error('Error processing session:', sessionData.session_id, error);
        // 继续执行，使用默认任务对象
      }

      // 根据状态分类任务，默认放入activeTasks
      if (processedTask.status === 'success') {
        completedTasksList.push(processedTask);
      } else {
        activeTasks.push(processedTask);
      }
    }

    // 设置第一个活跃任务为active
    if (activeTasks.length > 0 && activeTasks[0]) {
      activeTasks[0].active = true;
    }

    // 更新任务列表
    tasks.value = activeTasks;
    completedTasks.value = completedTasksList;
  } catch (error) {
    console.error('Error fetching tasks:', error);
    // 错误处理，保留空数组或添加错误状态任务
  }
};

// 组件挂载时获取数据
onMounted(() => {
  fetchTasksFromApi();
});



// 定义事件
const emit = defineEmits(['task-select']);

const activateTask = (taskId: string) => {

  tasks.value.forEach(task => {

    task.active = task.id === taskId;

  });

  completedTasks.value.forEach(task => {

    task.active = task.id === taskId;

  });

  // 触发任务选择事件
  emit('task-select', taskId);

};



const filteredTasks = computed(() => {

  if (!searchQuery.value) return tasks.value;

  const query = searchQuery.value.toLowerCase();

  return tasks.value.filter(task =>

    task.name.toLowerCase().includes(query) ||

    task.description.toLowerCase().includes(query) ||

    task.id.toLowerCase().includes(query)

  );

});



const filteredCompletedTasks = computed(() => {

  if (!searchQuery.value) return completedTasks.value;

  const query = searchQuery.value.toLowerCase();

  return completedTasks.value.filter(task =>

    task.name.toLowerCase().includes(query) ||

    task.description.toLowerCase().includes(query) ||

    task.id.toLowerCase().includes(query)

  );

});

/**
 * 创建新对话
 */
const createNewConversation = async () => {
  try {
    // 从localStorage获取userId，不存在则使用默认值1
    const userId = localStorage.getItem('userId') || '<user_id:1,tenant_id:1>';
    
    // 调用API创建新对话
    const newConversation = await ConversationAPI.createConversation(userId);
    
    if (newConversation) {
      console.log('New conversation created:', newConversation);
      
      // 刷新任务列表，显示新创建的对话
      await fetchTasksFromApi();
      
      // 触发任务选择事件，选择新创建的对话
      emit('task-select', newConversation.session_id);
    }
  } catch (error) {
    console.error('Error creating new conversation:', error);
    // 可以添加错误提示
  }
};

</script>



<style scoped>

.custom-scrollbar {

  scrollbar-width: thin;

  scrollbar-color: rgba(96, 165, 250, 0.5) transparent;

  overflow-y: auto;

}



.custom-scrollbar::-webkit-scrollbar {

  width: 8px;

}



.custom-scrollbar::-webkit-scrollbar-track {

  background: transparent;

  border-radius: 4px;

}



.custom-scrollbar::-webkit-scrollbar-thumb {

  background-color: rgba(96, 165, 250, 0.5);

  border-radius: 4px;

  border: 1px solid transparent;

  background-clip: padding-box;

}



.custom-scrollbar::-webkit-scrollbar-thumb:hover {

  background-color: rgba(96, 165, 250, 0.7);

}



.custom-scrollbar::-webkit-scrollbar-thumb:active {

  background-color: rgba(96, 165, 250, 0.9);

}

</style>