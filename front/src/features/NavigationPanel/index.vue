<template>
  <!-- Left Navigation Icons -->
  <div class="flex flex-col items-center gap-6 p-4 bg-black/20 backdrop-blur-sm border-r border-white/5 h-full">
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"
      :class="activeNavItem === 'search' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"
      @click="handleNavChange('search')"
    >
      <img src="@/assets/imgs/icon.png" class="h-5 w-5" alt="search" />
    </button>
      <button
      class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"
      :class="activeNavItem === 'overview' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"
      @click="handleNavChange('overview')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    </button>
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"
      :class="activeNavItem === 'tasks' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"
      @click="handleNavChange('tasks')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    </button>
    
  
    
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"
      :class="activeNavItem === 'analytics' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"
      @click="handleNavChange('analytics')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    </button>
    
    <div class="flex-grow"></div>
    
    <button
      class="w-9 h-9 flex items-center justify-center rounded-lg transition-all duration-300"
      :class="activeNavItem === 'settings' ? 'bg-sci-blue/20 text-sci-blue' : 'text-gray-400 hover:bg-white/10 hover:text-white'"
      @click="handleNavChange('settings')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const emit = defineEmits(['nav-change']);
const activeNavItem = ref('tasks');

const handleNavChange = (item: string) => {
  activeNavItem.value = item;
  emit('nav-change', item);
};
</script>
