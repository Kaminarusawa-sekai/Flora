<template>
  <button
    class="
      px-4 py-2 rounded-xl glass-panel glass-hover
      text-sm font-medium text-gray-100
      focus:outline-none focus:ring-2 focus:ring-sci-blue/50
      transition-all duration-300
    "
    :disabled="disabled"
    @click="handleClick"
  >
    <slot></slot>
  </button>
</template>

<script setup lang="ts">
const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  click: [];
}>();

const handleClick = () => {
  if (!props.disabled) {
    emit('click');
  }
};
</script>
