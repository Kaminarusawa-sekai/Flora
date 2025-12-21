<template>
  <div 
    class="
      group relative flex items-center w-full
      rounded-2xl border transition-all duration-300 ease-out
      bg-[#0a0c10]/60 backdrop-blur-xl
      border-white/10
      hover:border-white/20
      focus-within:border-cyan-500/50 focus-within:bg-[#0a0c10]/90 focus-within:shadow-hud-focus
    "
  >
    <div class="pl-4 pr-2 text-gray-500 transition-colors group-focus-within:text-cyan-400">
      <slot name="prefix">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </slot>
    </div>

    <input
      ref="inputRef"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="loading"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @keydown.enter="handleEnter"
      type="text"
      class="
        flex-1 bg-transparent border-none outline-none 
        text-sm text-gray-100 placeholder-gray-600 
        h-12 py-3 px-2
        disabled:cursor-not-allowed disabled:text-gray-500
      "
    />

    <div class="pr-2 pl-1">
      <transition name="fade" mode="out-in">
        <div v-if="loading" class="p-2 flex items-center justify-center">
          <div class="w-5 h-5 rounded-full border-2 border-white/10 border-t-cyan-400 animate-spin"></div>
        </div>
        
        <button 
          v-else
          @click="handleEnter"
          :disabled="!modelValue"
          class="
            p-2 rounded-xl transition-all duration-200
            flex items-center justify-center
          "
          :class="modelValue 
            ? 'text-cyan-400 hover:bg-cyan-400/10 hover:shadow-[0_0_10px_rgba(6,182,212,0.2)] cursor-pointer active:scale-95' 
            : 'text-gray-600 cursor-not-allowed opacity-50'
          "
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 rotate-90" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
          </svg>
        </button>
      </transition>
    </div>
    
    <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-1/3 h-[1px] bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent opacity-0 transition-all duration-500 group-focus-within:opacity-100 group-focus-within:w-2/3 blur-[1px]"></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
  modelValue: string;
  placeholder?: string;
  loading?: boolean;
}>();

const emit = defineEmits(['update:modelValue', 'submit']);
const inputRef = ref<HTMLInputElement | null>(null);

const handleEnter = () => {
  if (props.loading) return; // 防止重复提交
  emit('submit');
};

defineExpose({
  focus: () => inputRef.value?.focus()
});
</script>

<style scoped>
/* 简单的淡入淡出动画 */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: scale(0.8);
}
</style>