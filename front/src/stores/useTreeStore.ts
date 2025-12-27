import { defineStore } from 'pinia';
import type { Node, Edge } from '@vue-flow/core';

// 树形节点数据接口
export interface TreeNodeData {
  id: string;
  label: string;
  type: string;
  status?: 'idle' | 'running' | 'success' | 'error' | 'killed';
  progress?: number;
  time?: number;
  childrenCount?: number;
}

interface TreeState {
  nodes: Node<TreeNodeData>[];
  edges: Edge[];
  selectedNodeId: string | null;
  isDragging: boolean;
}

export const useTreeStore = defineStore('tree', {
  state: (): TreeState => ({
    nodes: [
      {
        id: 'node-1',
        type: 'tree',
        position: { x: 200, y: 50 },
        data: {
          id: 'TREE-001',
          label: 'Root Node',
          type: 'ROOT',
          status: 'running',
          progress: 45,
          time: 0,
          childrenCount: 2
        },
      },
      {
        id: 'node-2',
        type: 'tree',
        position: { x: 100, y: 300 },
        data: {
          id: 'TREE-002',
          label: 'Child Node A',
          type: 'CHILD',
          status: 'success',
          progress: 100,
          time: 120,
          childrenCount: 2
        },
      },
      {
        id: 'node-3',
        type: 'tree',
        position: { x: 300, y: 300 },
        data: {
          id: 'TREE-003',
          label: 'Child Node B',
          type: 'CHILD',
          status: 'running',
          progress: 30,
          time: 450,
          childrenCount: 0
        },
      },
      {
        id: 'node-4',
        type: 'tree',
        position: { x: 50, y: 550 },
        data: {
          id: 'TREE-004',
          label: 'Leaf Node A1',
          type: 'LEAF',
          status: 'success',
          progress: 100,
          time: 20,
          childrenCount: 0
        },
      },
      {
        id: 'node-5',
        type: 'tree',
        position: { x: 150, y: 550 },
        data: {
          id: 'TREE-005',
          label: 'Leaf Node A2',
          type: 'LEAF',
          status: 'error',
          progress: 80,
          time: 200,
          childrenCount: 0
        },
      },
    ],
    edges: [
      { id: 'e1-2', source: 'node-1', target: 'node-2', animated: true, style: { stroke: '#4ade80' } },
      { id: 'e1-3', source: 'node-1', target: 'node-3', animated: true, style: { stroke: '#2dd4bf' } },
      { id: 'e2-4', source: 'node-2', target: 'node-4', animated: false, style: { stroke: '#4ade80' } },
      { id: 'e2-5', source: 'node-2', target: 'node-5', animated: false, style: { stroke: '#f43f5e' } },
    ],
    selectedNodeId: null,
    isDragging: false,
  }),

  actions: {
    // 生成唯一ID
    generateId(): string {
      return `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    },

    // 生成唯一数据ID
    generateDataId(): string {
      return `TREE-${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`;
    },

    // 查找节点
    findNode(nodeId: string): Node<TreeNodeData> | undefined {
      return this.nodes.find(node => node.id === nodeId);
    },

    // 添加根节点
    addRootNode() {
      const newNode: Node<TreeNodeData> = {
        id: this.generateId(),
        type: 'tree',
        position: { x: 200, y: 50 },
        data: {
          id: this.generateDataId(),
          label: `Root Node ${this.nodes.filter(n => !this.edges.some(e => e.target === n.id)).length + 1}`,
          type: 'ROOT',
          status: 'idle',
          progress: 0,
          time: 0,
          childrenCount: 0
        },
      };
      this.nodes.push(newNode);
    },

    // 添加子节点
    addChildNode(parentId: string) {
      const parent = this.findNode(parentId);
      if (parent) {
        // 计算新节点位置（基于父节点位置）
        const newPosition = {
          x: parent.position.x + (Math.random() - 0.5) * 200,
          y: parent.position.y + 250
        };

        const newNode: Node<TreeNodeData> = {
          id: this.generateId(),
          type: 'tree',
          position: newPosition,
          data: {
            id: this.generateDataId(),
            label: `Child Node ${this.nodes.filter(n => this.edges.some(e => e.source === parentId)).length + 1}`,
            type: 'CHILD',
            status: 'idle',
            progress: 0,
            time: 0,
            childrenCount: 0
          },
        };
        
        this.nodes.push(newNode);
        
        // 创建连接边
        const newEdge: Edge = {
          id: `e${parentId}-${newNode.id}`,
          source: parentId,
          target: newNode.id,
          animated: true,
          style: { stroke: '#4ade80' }
        };
        
        this.edges.push(newEdge);
        
        // 更新父节点的子节点数量
        if (parent.data) {
          parent.data.childrenCount = (parent.data.childrenCount || 0) + 1;
        }
      }
    },

    // 删除节点
    deleteNode(nodeId: string) {
      // 删除相关边
      this.edges = this.edges.filter(edge => edge.source !== nodeId && edge.target !== nodeId);
      
      // 更新父节点的子节点数量
      const parentEdge = this.edges.find(edge => edge.target === nodeId);
      if (parentEdge) {
        const parent = this.findNode(parentEdge.source);
        if (parent && parent.data) {
          parent.data.childrenCount = Math.max(0, (parent.data.childrenCount || 0) - 1);
        }
      }
      
      // 删除节点
      this.nodes = this.nodes.filter(node => node.id !== nodeId);
      
      // 如果删除的是选中节点，清空选中状态
      if (this.selectedNodeId === nodeId) {
        this.selectedNodeId = null;
      }
    },

    // 选择节点
    selectNode(nodeId: string | null) {
      this.selectedNodeId = nodeId;
    },

    // 更新节点状态
    updateNodeStatus(nodeId: string, status: 'idle' | 'running' | 'success' | 'error' | 'killed') {
      const node = this.findNode(nodeId);
      if (node && node.data) {
        node.data.status = status;
      }
    },

    // 展开所有节点
    expandAll() {
      // Vue Flow 中展开/折叠通过位置调整实现，这里保持空实现
      console.log('Expand all nodes');
    },

    // 折叠所有节点
    collapseAll() {
      // Vue Flow 中展开/折叠通过位置调整实现，这里保持空实现
      console.log('Collapse all nodes');
    },

    // 设置拖拽状态
    setDragging(isDragging: boolean) {
      this.isDragging = isDragging;
    },
  },
});