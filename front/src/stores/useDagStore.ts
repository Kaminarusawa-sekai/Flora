import { defineStore } from 'pinia';
import type { Node, Edge } from '@vue-flow/core';
import { getTraceTopology } from '@/api/order';

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
  loading: boolean;
  error: string | null;
}

// DAG 缓存，使用 Map 存储已加载的 DAG 数据
const dagCache = new Map<string, { nodes: Node<NodeData>[]; edges: Edge[] }>();

export const useDagStore = defineStore('dag', {
  state: (): DagState => ({
    nodes: [],
    edges: [],
    selectedNodeId: null,
    isDragging: false,
    loading: false,
    error: null,
  }),
  
  getters: {
    // 获取缓存的 DAG 数据
    getCachedDag: () => (traceId: string) => {
      return dagCache.get(traceId);
    },
  },

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
    
    // 获取默认DAG结构
    getDefaultDag() {
      return {
         nodes: [
          { id: '1', type: 'glass', position: { x: 200, y: 200 }, data: { id: 'task-010', label: 'Default Root', type: 'AGENT', status: 'idle' as const, progress: 0, time: 0, childrenCount: 0 } },
        ],
        edges: [],
      };
    },
    
    // 获取初始DAG结构
    getInitialDag() {
      return {
        nodes: [
          { id: '1', type: 'glass', position: { x: 200, y: 50 }, data: { id: 'task-001', label: '任务节点', type: 'AGENT', status: 'running' as const, progress: 0, time: 0, childrenCount: 2 } },
          // { id: '2', type: 'glass', position: { x: 100, y: 300 }, data: { id: 'task-002', label: 'Data Group A', type: 'AGENT', status: 'success' as const, progress: 100, time: 120, childrenCount: 2 } },
          // { id: '3', type: 'glass', position: { x: 300, y: 300 }, data: { id: 'task-003', label: 'Data Group B', type: 'AGENT', status: 'running' as const, progress: 30, time: 450, childrenCount: 0 } },
          // { id: '4', type: 'glass', position: { x: 50, y: 550 }, data: { id: 'task-004', label: 'Worker 01', type: 'WORKER', status: 'success' as const, progress: 100, time: 20, childrenCount: 0 } },
          // { id: '5', type: 'glass', position: { x: 150, y: 550 }, data: { id: 'task-005', label: 'Worker 02', type: 'WORKER', status: 'error' as const, progress: 80, time: 200, childrenCount: 0 } },
        ],
        edges: [
          // { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#4ade80' } },
          // { id: 'e1-3', source: '1', target: '3', animated: true, style: { stroke: '#2dd4bf' } },
          // { id: 'e2-4', source: '2', target: '4', animated: false, style: { stroke: '#4ade80' } },
          // { id: 'e2-5', source: '2', target: '5', animated: false, style: { stroke: '#f43f5e' } },
        ],
      };
    },
    
    // 缓存 DAG 数据
    cacheDagData(traceId: string, dagData: { nodes: Node<NodeData>[]; edges: Edge[] }) {
      dagCache.set(traceId, dagData);
    },
    
    // 加载 DAG 数据（优先从缓存获取，缓存不存在则从 API 获取）
    async loadDagByTraceId(traceId: string) {
      try {
        this.loading = true;
        this.error = null;
        
        // 首先检查缓存
        const cachedDag = this.getCachedDag(traceId);
        if (cachedDag) {
          console.log('Using cached DAG data for trace:', traceId);
          this.nodes = cachedDag.nodes;
          this.edges = cachedDag.edges;
          this.selectedNodeId = null;
          return;
        }
        
        // 缓存不存在，从 API 获取
        console.log('Loading DAG data from API for trace:', traceId);
        const dagData = await getTraceTopology(traceId);
        
        // 转换数据类型
        const typedNodes = dagData.nodes as Node<NodeData>[];
        const typedEdges = dagData.edges as Edge[];
        
        // 检查是否获取到值
        if (!typedNodes || typedNodes.length === 0) {
          console.log('No DAG data found from API, using initial DAG structure');
          const initialDag = this.getInitialDag();
          this.nodes = initialDag.nodes;
          this.edges = initialDag.edges;
          this.selectedNodeId = null;
          
          // 缓存初始 DAG 数据
          this.cacheDagData(traceId, initialDag);
        } else {
          // 获取到值，更新状态
          this.nodes = typedNodes;
          this.edges = typedEdges;
          this.selectedNodeId = null;
          
          // 缓存数据
          this.cacheDagData(traceId, { nodes: typedNodes, edges: typedEdges });
        }
      } catch (error) {
        console.error('Failed to load DAG data:', error);
        this.error = error instanceof Error ? error.message : 'Failed to load DAG data';
        
        // 加载失败时使用默认 DAG 结构
        const defaultDag = this.getDefaultDag();
        this.nodes = defaultDag.nodes;
        this.edges = defaultDag.edges;
        this.selectedNodeId = null;
        
        // 缓存默认 DAG 数据
        this.cacheDagData(traceId, defaultDag);
      } finally {
        this.loading = false;
      }
    },
    
    // 废弃：原 loadDagByTaskId 方法，保留兼容性
    loadDagByTaskId(taskId: string) {
      console.warn('loadDagByTaskId is deprecated, use loadDagByTraceId instead');
      return this.loadDagByTraceId(taskId);
    },
  },
});