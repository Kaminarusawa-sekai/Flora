<template>
  <div class="relative">
    <input
      :value="modelValue"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      :placeholder="placeholder"
      class="hud-input w-full"
      ref="inputRef"
      @keydown.enter="handleEnter"
    />
    <slot name="suffix"></slot>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  modelValue: string;
  placeholder?: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: string];
  'enter': [];
}>();

const handleEnter = () => {
  emit('enter');
};
</script>
