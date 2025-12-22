<template>

  <div class="h-full flex">

    <!-- Left Navigation Icons -->

    <div class="flex flex-col items-center gap-6 p-4 bg-black/20 backdrop-blur-sm border-r border-white/5">

      <button

        class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"

        :class="activeNavItem === 'search' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"

        @click="activeNavItem = 'search'"

      >

        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">

          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />

        </svg>

      </button>

     

      <button

        class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"

        :class="activeNavItem === 'tasks' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"

        @click="activeNavItem = 'tasks'"

      >

        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">

          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />

        </svg>

      </button>

     

      <button

        class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"

        :class="activeNavItem === 'completed' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"

        @click="activeNavItem = 'completed'"

      >

        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">

          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />

        </svg>

      </button>

     

      <button

        class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"

        :class="activeNavItem === 'analytics' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"

        @click="activeNavItem = 'analytics'"

      >

        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">

          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />

        </svg>

      </button>

     

      <div class="flex-grow"></div>

     

      <button

        class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"

        :class="activeNavItem === 'settings' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"

        @click="activeNavItem = 'settings'"

      >

        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">

          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>

      </button>

    </div>

   

    <!-- Main Task Content -->

    <GlassCard class="h-full flex flex-col relative">

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

      </div>



      <div class="flex-1 min-h-0 py-2 space-y-6 overflow-y-auto pr-1 custom-scrollbar">

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

          :class="task.active ? 'border-sci-blue/30 bg-sci-blue/5' : ''"

          @click="activateTask(task.id)"

        >

          <div class="p-5 flex items-center gap-4">

            <StatusDot :status="task.status" />

           

            <div class="flex-grow">

              <div class="flex justify-between items-center mb-1">

                <span class="text-sm font-medium text-gray-200 group-hover:text-white transition-colors">{{ task.name }}</span>

                <span class="text-[10px] font-mono text-gray-600 group-hover:text-sci-blue">{{ task.id }}</span>

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

        >

          <div class="p-5 flex items-center gap-4">

            <StatusDot :status="task.status" />

           

            <div class="flex-grow">

              <div class="flex justify-between items-center mb-1">

                <span class="text-sm font-medium text-gray-400 group-hover:text-gray-300 transition-colors">{{ task.name }}</span>

                <span class="text-[10px] font-mono text-gray-600 group-hover:text-sci-blue">{{ task.id }}</span>

              </div>

              <p class="text-xs text-gray-500 line-clamp-1">{{ task.description }}</p>

            </div>

          </div>

        </GlassCard>

      </div>



      <div class="mt-4 pt-4 border-t border-white/5 flex items-center justify-between">

        <div class="flex items-center gap-2">

          <StatusDot status="running" size="sm" />

          <span class="text-xs font-mono text-sci-green">SYSTEM ONLINE</span>

        </div>

        <button class="text-gray-500 hover:text-white transition-colors">

          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>

        </button>

      </div>

    </GlassCard>

  </div>

</template>



<script setup lang="ts">

import { ref, computed } from 'vue';

import GlassCard from '@/components/ui/GlassCard.vue';

import StatusDot from '@/components/ui/StatusDot.vue';

import InputHud from '@/components/ui/InputHud.vue';



const searchQuery = ref('');

const activeNavItem = ref('tasks');



interface Task {

  id: string;

  name: string;

  description: string;

  status: 'idle' | 'running' | 'success' | 'error' | 'pending';

  active?: boolean;

}



const tasks = ref<Task[]>([

  {

    id: 'TSK-01',

    name: 'Data Pipeline',

    description: 'ETL process for customer data',

    status: 'running',

    active: true,

  },

  {

    id: 'TSK-02',

    name: 'Data Backup',

    description: 'Data backup task',

    status: 'pending',

    active: false,

  },

  {

    id: 'TSK-03',

    name: 'ETL Process',

    description: 'ETL process for customer data',

    status: 'running',

    active: false,

  },

  {

    id: 'TSK-04',

    name: 'Data Backup',

    description: 'Data backup task',

    status: 'pending',

    active: false,

  },

]);



const completedTasks = ref<Task[]>([

  {

    id: 'TSK-05',

    name: 'Data Backup',

    description: 'Backup customer data',

    status: 'success',

  },

  {

    id: 'TSK-06',

    name: 'ETL Process',

    description: 'ETL process for customer data',

    status: 'success',

  },

  {

    id: 'TSK-07',

    name: 'Data Backup',

    description: 'Backup customer data',

    status: 'success',

  },

  {

    id: 'TSK-08',

    name: 'ETL Process',

    description: 'ETL process for customer data',

    status: 'success',

  },

]);



// 定义事件
const emit = defineEmits(['task-select']);

const activateTask = (taskId: string) => {

  tasks.value.forEach(task => {

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

</script>



<style scoped>

.custom-scrollbar {

  scrollbar-width: thin;

  scrollbar-color: rgba(139, 92, 246, 0.3) transparent;

}



.custom-scrollbar::-webkit-scrollbar {

  width: 6px;

}



.custom-scrollbar::-webkit-scrollbar-track {

  background: transparent;

}



.custom-scrollbar::-webkit-scrollbar-thumb {

  background-color: rgba(139, 92, 246, 0.3);

  border-radius: 3px;

}



.custom-scrollbar::-webkit-scrollbar-thumb:hover {

  background-color: rgba(139, 92, 246, 0.5);

}

</style>