import { defineStore } from 'pinia';
import type { Node, Edge } from '@vue-flow/core';

interface NodeData {
  id: string;
  label: string;
  type: string;
  status: 'idle' | 'running' | 'success' | 'error' | 'killed';
  progress: number;
  time: number;
  childrenCount?: number;
}

interface DagState {
  nodes: Node<NodeData>[];
  edges: Edge[];
  selectedNodeId: string | null;
  isDragging: boolean;
}

export const useDagStore = defineStore('dag', {
  state: (): DagState => ({
    nodes: [
      {
        id: '1',
        type: 'glass',
        position: { x: 200, y: 50 },
        data: {
          id: 'task-001',
          label: 'Root Agent',
          type: 'AGENT',
          status: 'running',
          progress: 45,
          time: 0,
          childrenCount: 2
        },
      },
      {
        id: '2',
        type: 'glass',
        position: { x: 100, y: 300 },
        data: {
          id: 'task-002',
          label: 'Data Group A',
          type: 'AGENT',
          status: 'success',
          progress: 100,
          time: 120,
          childrenCount: 2
        },
      },
      {
        id: '3',
        type: 'glass',
        position: { x: 300, y: 300 },
        data: {
          id: 'task-003',
          label: 'Data Group B',
          type: 'AGENT',
          status: 'running',
          progress: 30,
          time: 450,
          childrenCount: 0
        },
      },
      {
        id: '4',
        type: 'glass',
        position: { x: 50, y: 550 },
        data: {
          id: 'task-004',
          label: 'Worker 01',
          type: 'WORKER',
          status: 'success',
          progress: 100,
          time: 20,
          childrenCount: 0
        },
      },
      {
        id: '5',
        type: 'glass',
        position: { x: 150, y: 550 },
        data: {
          id: 'task-005',
          label: 'Worker 02',
          type: 'WORKER',
          status: 'error',
          progress: 80,
          time: 200,
          childrenCount: 0
        },
      },
    ],
    edges: [
      { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#4ade80' } },
      { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#2dd4bf' } },
      { id: 'e2-4', source: '2', target: '4', animated: false, style: { stroke: '#4ade80' } },
      { id: 'e2-5', source: '2', target: '5', animated: false, style: { stroke: '#f43f5e' } },
    ],
    selectedNodeId: null,
    isDragging: false,
  }),

  actions: {
    addNode(node: Node<NodeData>) {
      this.nodes.push(node);
    },
    removeNode(nodeId: string) {
      this.nodes = this.nodes.filter(node => node.id !== nodeId);
      this.edges = this.edges.filter(edge => edge.source !== nodeId && edge.target !== nodeId);
    },
    updateNodeStatus(nodeId: string, status: 'idle' | 'running' | 'success' | 'error' | 'killed') {
      const node = this.nodes.find(n => n.id === nodeId);
      if (node && node.data) {
        node.data.status = status;
      }
    },
    selectNode(nodeId: string | null) {
      this.selectedNodeId = nodeId;
    },
    setDragging(isDragging: boolean) {
      this.isDragging = isDragging;
    },
  },
});