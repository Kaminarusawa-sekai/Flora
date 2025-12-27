<template>
  <div class="tree-item">
    <!-- 节点行 -->
    <div 
      class="flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-all hover:bg-white/5 group"
      :class="{ 'bg-white/10': node.selected }"
      :style="{ paddingLeft: `${level * 24 + 8}px` }"
      @click="handleSelect"
    >
      <!-- 展开/折叠按钮 -->
      <button 
        v-if="node.children && node.children.length > 0"
        class="w-5 h-5 flex items-center justify-center text-gray-400 hover:text-white transition"
        @click="handleToggleExpand"
      >
        <svg 
          class="w-4 h-4 transition-transform"
          :class="{ 'rotate-90': node.expanded }"
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
      <div v-else class="w-5"></div>
      
      <!-- 节点图标 -->
      <svg class="w-5 h-5 text-sci-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
      
      <!-- 节点标签 -->
      <span class="flex-1 text-white">{{ node.label }}</span>
      
      <!-- 操作按钮 -->
      <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <!-- 添加子节点按钮 -->
        <button 
          class="p-1.5 rounded hover:bg-white/10 text-gray-400 hover:text-white transition"
          @click="handleAddChild"
          title="Add Child"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
        </button>
        
        <!-- 删除节点按钮 -->
        <button 
          class="p-1.5 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition"
          @click="handleDelete"
          title="Delete"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
    
    <!-- 子节点 -->
    <div 
      v-if="node.children && node.children.length > 0" 
      class="space-y-1 ml-4"
      v-show="node.expanded"
    >
      <TreeItem
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :level="level + 1"
        @select="$emit('select', $event)"
        @add-child="$emit('add-child', $event)"
        @delete="$emit('delete', $event)"
        @toggle-expand="$emit('toggle-expand', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
// 树形节点接口
export interface TreeNode {
  id: string;
  label: string;
  children?: TreeNode[];
  expanded?: boolean;
  selected?: boolean;
}

// Props
const props = withDefaults(defineProps<{
  node: TreeNode;
  level?: number;
}>(), {
  level: 0
});

// Emits
const emit = defineEmits<{
  select: [id: string];
  'add-child': [parentId: string];
  delete: [id: string];
  'toggle-expand': [id: string];
}>();

const handleSelect = () => {
  emit('select', props.node.id);
};

// 添加子节点事件
const handleAddChild = (event: MouseEvent) => {
  event.stopPropagation();
  emit('add-child', props.node.id);
};

// 删除节点事件
const handleDelete = (event: MouseEvent) => {
  event.stopPropagation();
  emit('delete', props.node.id);
};

// 切换展开/折叠事件
const handleToggleExpand = (event: MouseEvent) => {
  event.stopPropagation();
  emit('toggle-expand', props.node.id);
};
</script>

<style scoped>
.tree-item {
  transition: all 0.3s ease;
}
</style>