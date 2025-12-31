<script setup lang="ts">
import { computed, ref } from 'vue';
import { Handle, Position } from '@vue-flow/core';

interface CurrentTask {
  task_id: string;
  trace_id: string;
  step: string;
  reported_at: number;
}

interface Runtime {
  is_alive: boolean;
  status_label: string;
  last_seen_seconds_ago: number;
  current_task?: CurrentTask;
}

interface Meta {
  type: string;
  is_leaf: boolean;
  weight: number;
  description: string;
}

interface Visual {
  progress: number;
  timeElapsedMs: number;
  statusIcon?: string;
  statusColor?: string;
}

interface NodeData {
  agentId: string;
  id: string;
  label: string;
  type: string; // e.g., 'ROOT'
  meta: Meta;
  runtime: Runtime;
  visual: Visual;
  childrenCount: number;
  depth: number;
  traceId: string;
}

const props = defineProps<{
  data: NodeData;
  selected: boolean;
  class?: string;
}>();

// ===== 状态计算 =====
const status = computed(() => props.data.runtime?.status_label || 'UNKNOWN');
const isRunning = computed(() => status.value === 'BUSY');
const isFailed = computed(() => status.value === 'ERROR');
const isKilled = computed(() => status.value === 'KILLED');
const isSuccess = computed(() => status.value === 'SUCCESS');
const isAlive = computed(() => props.data.runtime?.is_alive ?? false);

// ===== 进度 & 时间 =====
const progress = computed(() => props.data.visual?.progress ?? 0);
const timeElapsedMs = computed(() => props.data.visual?.timeElapsedMs ?? 0);
const progressStyle = computed(() => ({ width: `${progress.value}%` }));

// ===== 折叠控制 =====
const showTask = ref(false);
const showMeta = ref(false);

// ===== 格式化时间 =====
const formatTime = (timestamp: number): string => {
  if (!timestamp) return '—';
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
};

// ===== 子节点数 =====
const childrenCount = computed(() => props.data.childrenCount || 0);
</script>

<template>
  <div
    class="glass-card w-[320px] p-4 relative group overflow-hidden"
    :class="{
      'selected': selected,
      'card-killed': isKilled,
      'status-running': isRunning,
      'status-success': isSuccess,
      'status-failed': isFailed
    }"
  >
    <Handle type="target" :position="Position.Top" class="!opacity-0 !w-full !h-4 !top-0" />

    <!-- Header -->
    <div class="flex justify-between items-start mb-3">
      <div class="flex flex-col">
        <span class="text-xs font-medium text-gray-400 tracking-wide uppercase">
          {{ data.meta?.type || data.type }}
        </span>
        <h3 class="text-sm font-bold text-white leading-tight mt-0.5 max-w-[180px] truncate">
          {{ data.label }}
        </h3>
        <div class="text-[10px] text-gray-500 mt-1">
          Agent: {{ data.agentId }}
        </div>
      </div>

      <div class="px-2 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] text-gray-400 backdrop-blur-md whitespace-nowrap">
        #{{ data.id }}
      </div>
    </div>

    <!-- Status Line -->
    <div class="flex items-center gap-2 text-[11px] text-gray-300 mb-3">
      <span :class="{
        'text-teal-400': isRunning,
        'text-rose-500': isFailed,
        'text-emerald-400': isSuccess,
        'text-amber-500': !isRunning && !isFailed && !isSuccess
      }">
        {{ status }}
      </span>
      <span v-if="!isAlive" class="text-rose-400">● OFFLINE</span>
      <span v-else class="text-green-400">● LIVE</span>
      <span v-if="data.runtime?.last_seen_seconds_ago !== undefined">
        ({{ data.runtime.last_seen_seconds_ago }}s ago)
      </span>
    </div>

    <!-- Progress & Time -->
    <div class="mt-2 mb-2">
      <div class="text-3xl font-bold tracking-tight text-white flex items-baseline gap-1">
        {{ progress }}<span class="text-lg text-gray-500">%</span>
      </div>
      <div class="text-[10px] text-gray-500 mt-1">{{ timeElapsedMs }}ms elapsed</div>
    </div>

    <div class="relative h-2 w-full bg-white/10 rounded-full overflow-hidden mb-4">
      <div
        class="absolute top-0 left-0 h-full rounded-full transition-all duration-700 ease-out"
        :class="isFailed || isKilled ? 'gradient-bar-failed' : 'gradient-bar-success'"
        :style="progressStyle"
      ></div>
    </div>

    <!-- Current Task (Collapsible) -->
    <div v-if="data.runtime?.current_task" class="mb-3">
      <div
        class="flex justify-between items-center text-[11px] font-medium text-gray-400 cursor-pointer"
        @click="showTask = !showTask"
      >
        <span>Current Task</span>
        <span>{{ showTask ? '▲' : '▼' }}</span>
      </div>
      <div v-show="showTask" class="text-[10px] text-gray-300 mt-1 space-y-1 bg-black/20 p-2 rounded">
        <div>Task ID: <span class="font-mono">{{ data.runtime.current_task.task_id }}</span></div>
        <div>Step: {{ data.runtime.current_task.step }}</div>
        <div>Trace: <span class="font-mono">{{ data.runtime.current_task.trace_id }}</span></div>
        <div>Reported: {{ formatTime(data.runtime.current_task.reported_at) }}</div>
      </div>
    </div>

    <!-- Meta Info (Collapsible) -->
    <div class="mb-3">
      <div
        class="flex justify-between items-center text-[11px] font-medium text-gray-400 cursor-pointer"
        @click="showMeta = !showMeta"
      >
        <span>Meta Info</span>
        <span>{{ showMeta ? '▲' : '▼' }}</span>
      </div>
      <div v-show="showMeta" class="text-[10px] text-gray-300 mt-1 space-y-1 bg-black/20 p-2 rounded">
        <div v-if="data.meta?.description">Desc: {{ data.meta.description }}</div>
        <div>Leaf: {{ data.meta?.is_leaf ? 'Yes' : 'No' }}</div>
        <div>Weight: {{ data.meta?.weight }}</div>
        <div>Depth: {{ data.depth }}</div>
        <div>Children: {{ childrenCount }}</div>
        <div>Trace ID: <span class="font-mono">{{ data.traceId }}</span></div>
      </div>
    </div>

    <!-- Avatars / Children Preview -->
    <div class="flex items-center justify-between pt-2 border-t border-white/5">
      <div class="flex -space-x-2">
        <div class="w-5 h-5 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 border border-[#1e1e23]"></div>
        <div class="w-5 h-5 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 border border-[#1e1e23]"></div>
        <div v-if="childrenCount > 0" class="w-5 h-5 rounded-full bg-[#2a2a30] border border-[#1e1e23] flex items-center justify-center text-[7px] text-gray-400">
          +{{ childrenCount }}
        </div>
      </div>
    </div>

    <!-- Killed Overlay -->
    <div v-if="isKilled" class="absolute inset-0 bg-black/60 backdrop-blur-[1px] z-10 flex items-center justify-center">
      <span class="text-rose-500 font-bold tracking-widest border border-rose-500/30 px-3 py-1 rounded bg-rose-500/10">TERMINATED</span>
    </div>

    <Handle type="source" :position="Position.Bottom" class="!opacity-0 !w-full !h-4 !bottom-0" />
  </div>
</template>

<style scoped>
/* 保留你原有的 glass-card 和状态样式 */
.glass-card {
  background: rgba(30, 30, 35, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 
    0 20px 40px -10px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.glass-card.selected {
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 
    0 0 0 4px rgba(255, 255, 255, 0.05),
    0 20px 40px -10px rgba(0, 0, 0, 0.7);
  transform: translateY(-2px) scale(1.02);
}

.gradient-bar-success {
  background: linear-gradient(90deg, #4ade80 0%, #2dd4bf 50%, #3b82f6 100%);
  box-shadow: 0 0 20px rgba(45, 212, 191, 0.4);
}

.gradient-bar-failed {
  background: linear-gradient(90deg, #f87171 0%, #f43f5e 50%, #e11d48 100%);
  box-shadow: 0 0 20px rgba(244, 63, 94, 0.4);
}

.status-running {
  border-color: rgba(45, 212, 191, 0.5);
  box-shadow: 0 0 10px rgba(45, 212, 191, 0.2);
}

.status-success {
  border-color: rgba(74, 222, 128, 0.5);
  box-shadow: 0 0 10px rgba(74, 222, 128, 0.2);
}

.status-failed {
  border-color: rgba(244, 63, 94, 0.5);
  box-shadow: 0 0 10px rgba(244, 63, 94, 0.2);
}

.card-killed {
  filter: grayscale(1) brightness(0.5);
  border-color: rgba(255, 50, 50, 0.3);
  transform: scale(0.95);
}
</style>