<template>
  <div 
    class="status-dot"
    :class="status"
  ></div>
</template>

<script setup lang="ts">
type Status = 'idle' | 'running' | 'success' | 'error';

const props = defineProps<{
  status: Status;
}>();
</script>
