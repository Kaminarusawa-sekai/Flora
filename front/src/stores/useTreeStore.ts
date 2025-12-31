import { defineStore } from 'pinia';
import type { Node, Edge } from '@vue-flow/core';
import AgentAPI from '../api/agent.js';

// 树形节点数据接口
interface Meta {
  type: string;
  is_leaf: boolean;
  weight: number;
  description: string;
  [key: string]: any;
}

interface CurrentTask {
  task_id: string;
  trace_id: string;
  step: string;
  reported_at: number;
  [key: string]: any;
}

interface LastCompletedTask {
  task_id: string;
  status: 'COMPLETED' | 'FAILED';
  end_time: string;
  duration: number;
  [key: string]: any;
}

interface Runtime {
  is_alive: boolean;
  status_label: 'IDLE' | 'BUSY' | 'OFFLINE';
  last_seen_seconds_ago: number;
  current_task?: CurrentTask;
  last_completed_task?: LastCompletedTask;
}

interface Visual {
  statusColor: string;
  statusIcon: string;
  progress: number | null;
  timeElapsedMs: number;
}

export interface TreeNodeData {
  // 核心标识
  agentId: string;
  id?: string;
  label: string;
  type: string;
  
  // 元数据
  meta: Meta;
  
  // 运行时状态
  runtime: Runtime;
  
  // 前端计算辅助字段
  visual: Visual;
  
  // 拓扑信息
  childrenCount: number;
  depth?: number;
  parentId?: string;
  
  // 可观测性
  traceId?: string;
  
  // 旧字段（向后兼容）
  status?: 'idle' | 'running' | 'success' | 'error' | 'killed';
  progress?: number;
  time?: number;
}

interface TreeState {
  nodes: Node<TreeNodeData>[];
  edges: Edge[];
  selectedNodeId: string | null;
  isDragging: boolean;
  // WebSocket相关状态
  wsConnections: Map<string, WebSocket>;
  isWsConnected: boolean;
  wsError: string | null;
  // 默认树结构，用于在没有获取到数据时显示
  defaultNodes: Node<TreeNodeData>[];
  defaultEdges: Edge[];
}

export const useTreeStore = defineStore('tree', {
  state: (): TreeState => {
    // 默认树结构数据
     const defaultNodes: Node<TreeNodeData>[] = [
      {
        id: 'node-1',
        type: 'tree',
        position: { x: 200, y: 50 },
        data: {
          agentId: 'TREE-001',
          id: 'TREE-001',
          label: 'Root Node',
          type: 'ROOT',
          meta: {
            type: 'LLM-Worker',
            is_leaf: false,
            weight: 1.0,
            description: 'Root node of the tree'
          },
          runtime: {
            is_alive: true,
            status_label: 'BUSY',
            last_seen_seconds_ago: 1,
            current_task: {
              task_id: 'task-123',
              trace_id: 'trace-abc',
              step: 'generating response',
              reported_at: Date.now()
            }
          },
          visual: {
            statusColor: '#FFA500',
            statusIcon: '🔄',
            progress: 45,
            timeElapsedMs: 5000
          },
          childrenCount: 2,
          depth: 0,
          traceId: 'trace-abc'
        },
      },
      {
        id: 'node-2',
        type: 'tree',
        position: { x: 100, y: 300 },
        data: {
          agentId: 'TREE-002',
          id: 'TREE-002',
          label: 'Child Node A',
          type: 'CHILD',
          meta: {
            type: 'Search-Tool',
            is_leaf: false,
            weight: 0.8,
            description: 'Search tool agent'
          },
          runtime: {
            is_alive: true,
            status_label: 'IDLE',
            last_seen_seconds_ago: 5,
            last_completed_task: {
              task_id: 'task-456',
              status: 'COMPLETED',
              end_time: new Date().toISOString(),
              duration: 120
            }
          },
          visual: {
            statusColor: '#4ade80',
            statusIcon: '⏸️',
            progress: 100,
            timeElapsedMs: 0
          },
          childrenCount: 2,
          depth: 1,
          parentId: 'node-1'
        },
      },
      {
        id: 'node-3',
        type: 'tree',
        position: { x: 300, y: 300 },
        data: {
          agentId: 'TREE-003',
          id: 'TREE-003',
          label: 'Child Node B',
          type: 'CHILD',
          meta: {
            type: 'LLM-Worker',
            is_leaf: true,
            weight: 0.9,
            description: 'LLM inference agent'
          },
          runtime: {
            is_alive: true,
            status_label: 'BUSY',
            last_seen_seconds_ago: 2,
            current_task: {
              task_id: 'task-789',
              trace_id: 'trace-def',
              step: 'processing',
              reported_at: Date.now() - 3000
            }
          },
          visual: {
            statusColor: '#FFA500',
            statusIcon: '🔄',
            progress: 30,
            timeElapsedMs: 3000
          },
          childrenCount: 0,
          depth: 1,
          parentId: 'node-1',
          traceId: 'trace-def'
        },
      },
      {
        id: 'node-4',
        type: 'tree',
        position: { x: 50, y: 550 },
        data: {
          agentId: 'TREE-004',
          id: 'TREE-004',
          label: 'Leaf Node A1',
          type: 'LEAF',
          meta: {
            type: 'Tool-Exec',
            is_leaf: true,
            weight: 0.7,
            description: 'Tool execution agent'
          },
          runtime: {
            is_alive: true,
            status_label: 'IDLE',
            last_seen_seconds_ago: 10,
            last_completed_task: {
              task_id: 'task-abc',
              status: 'COMPLETED',
              end_time: new Date().toISOString(),
              duration: 20
            }
          },
          visual: {
            statusColor: '#4ade80',
            statusIcon: '⏸️',
            progress: 100,
            timeElapsedMs: 0
          },
          childrenCount: 0,
          depth: 2,
          parentId: 'node-2'
        },
      },
      {
        id: 'node-5',
        type: 'tree',
        position: { x: 150, y: 550 },
        data: {
          agentId: 'TREE-005',
          id: 'TREE-005',
          label: 'Leaf Node A2',
          type: 'LEAF',
          meta: {
            type: 'Tool-Exec',
            is_leaf: true,
            weight: 0.7,
            description: 'Tool execution agent'
          },
          runtime: {
            is_alive: false,
            status_label: 'OFFLINE',
            last_seen_seconds_ago: 300,
            last_completed_task: {
              task_id: 'task-def',
              status: 'FAILED',
              end_time: new Date().toISOString(),
              duration: 200
            }
          },
          visual: {
            statusColor: '#f43f5e',
            statusIcon: '🔴',
            progress: 80,
            timeElapsedMs: 0
          },
          childrenCount: 0,
          depth: 2,
          parentId: 'node-2'
        },
      },
    ];

    const defaultEdges: Edge[] = [
      { id: 'e1-2', source: 'node-1', target: 'node-2', animated: true, style: { stroke: '#4ade80' } },
      { id: 'e1-3', source: 'node-1', target: 'node-3', animated: true, style: { stroke: '#2dd4bf' } },
      { id: 'e2-4', source: 'node-2', target: 'node-4', animated: false, style: { stroke: '#4ade80' } },
      { id: 'e2-5', source: 'node-2', target: 'node-5', animated: false, style: { stroke: '#f43f5e' } },
    ];

    return {
      // 初始时使用默认树结构
      nodes: defaultNodes,
      edges: defaultEdges,
      selectedNodeId: null,
      isDragging: false,
      // WebSocket相关状态初始化
      wsConnections: new Map<string, WebSocket>(),
      isWsConnected: false,
      wsError: null,
      // 保留默认结构用于回退
      defaultNodes,
      defaultEdges,
    };
  },

  actions: {
    // 生成唯一ID
    generateId(): string {
      return `node-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    },

    // 根据根节点ID获取对应树结构
    getTreeByRootId(rootId: string) {
      // 找到根节点
      const rootNode = this.nodes.find(node => node.id === rootId);
      if (!rootNode) {
        // 如果找不到根节点，尝试使用默认树结构
        const defaultRootNode = this.defaultNodes.find(node => node.id === rootId);
        if (!defaultRootNode) {
          // 如果默认树结构中也没有该根节点，返回默认树结构的副本
          return {
            nodes: [...this.defaultNodes],
            edges: [...this.defaultEdges]
          };
        }

        // 递归查找默认树结构中的所有子节点
        const getChildNodes = (nodeId: string): Node<TreeNodeData>[] => {
          const childNodes = this.defaultNodes.filter(node => 
            node.data?.parentId === nodeId || 
            this.defaultEdges.some(edge => edge.source === nodeId && edge.target === node.id)
          );

          return [
            ...childNodes,
            ...childNodes.flatMap(child => getChildNodes(child.id))
          ];
        };

        // 获取默认树结构中的相关节点和边
        const relatedNodes = [defaultRootNode, ...getChildNodes(rootId)];
        const relatedNodeIds = new Set(relatedNodes.map(node => node.id));

        const relatedEdges = this.defaultEdges.filter(edge => 
          relatedNodeIds.has(edge.source) && relatedNodeIds.has(edge.target)
        );

        return {
          nodes: relatedNodes,
          edges: relatedEdges
        };
      }

      // 递归查找所有子节点
      const getChildNodes = (nodeId: string): Node<TreeNodeData>[] => {
        // 找到所有直接子节点（通过边或parentId）
        const childNodes = this.nodes.filter(node => 
          node.data?.parentId === nodeId || 
          this.edges.some(edge => edge.source === nodeId && edge.target === node.id)
        );

        // 递归查找子节点的子节点
        return [
          ...childNodes,
          ...childNodes.flatMap(child => getChildNodes(child.id))
        ];
      };

      // 获取所有相关节点
      const relatedNodes = [rootNode, ...getChildNodes(rootId)];
      const relatedNodeIds = new Set(relatedNodes.map(node => node.id));

      // 获取所有相关边
      const relatedEdges = this.edges.filter(edge => 
        relatedNodeIds.has(edge.source) && relatedNodeIds.has(edge.target)
      );

      return {
        nodes: relatedNodes,
        edges: relatedEdges
      };
    },

    /**
     * 通过WebSocket连接获取指定Agent的树结构
     * @param agentId - Agent ID
     */
    connectToAgentTreeWebSocket(agentId: string) {
      // 如果已经有连接，先关闭
      if (this.wsConnections.has(agentId)) {
        this.closeAgentTreeWebSocket(agentId);
      }

      // 创建WebSocket连接
      const ws = AgentAPI.createAgentTreeWebSocket(agentId, {
        onOpen: () => {
          this.isWsConnected = true;
          this.wsError = null;
          console.log(`Connected to agent ${agentId} WebSocket`);
        },
        onMessage: (processedData) => {
          // 只有在获取到有效数据时才更新树结构
          if (processedData && processedData.nodes && processedData.nodes.length > 0) {
            this.nodes = processedData.nodes;
            this.edges = processedData.edges;
            console.log(`Received agent ${agentId} tree update`);
          } else {
            console.warn(`Received empty tree data from agent ${agentId}, keeping default tree`);
          }
        },
        onError: (error) => {
          this.wsError = `WebSocket error for agent ${agentId}: ${error.message}`;
          console.error(this.wsError);
          // 错误时保持默认树结构不变
        },
        onClose: () => {
          this.isWsConnected = false;
          this.wsConnections.delete(agentId);
          console.log(`Disconnected from agent ${agentId} WebSocket`);
          // 关闭时保持当前树结构不变
        }
      });

      // 保存WebSocket连接
      this.wsConnections.set(agentId, ws);
    },

    /**
     * 关闭指定Agent的WebSocket连接
     * @param agentId - Agent ID
     */
    closeAgentTreeWebSocket(agentId: string) {
      const ws = this.wsConnections.get(agentId);
      if (ws) {
        AgentAPI.closeAgentTreeWebSocket(ws);
        this.wsConnections.delete(agentId);
      }
    },

    /**
     * 关闭所有WebSocket连接
     */
    closeAllWebSocketConnections() {
      this.wsConnections.forEach((ws, agentId) => {
        AgentAPI.closeAgentTreeWebSocket(ws);
      });
      this.wsConnections.clear();
      this.isWsConnected = false;
    },

    /**
     * 刷新指定Agent的树结构
     * @param agentId - Agent ID
     */
    refreshAgentTree(agentId: string) {
      const ws = this.wsConnections.get(agentId);
      if (ws) {
        AgentAPI.refreshAgentTree(ws);
        console.log(`Sent refresh command to agent ${agentId}`);
      } else {
        console.error(`No WebSocket connection found for agent ${agentId}`);
      }
    },

    /**
     * 通过WebSocket获取树结构后，根据根节点ID筛选
     * @param agentId - Agent ID
     * @param rootId - 根节点ID
     */
    getTreeByWebSocket(agentId: string, rootId: string) {
      // 如果还没有连接，先建立连接
      if (!this.wsConnections.has(agentId)) {
        this.connectToAgentTreeWebSocket(agentId);
      }

      // 使用已有的树结构数据进行筛选
      return this.getTreeByRootId(rootId);
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
      const agentId = this.generateDataId();
      const newNode: Node<TreeNodeData> = {
        id: this.generateId(),
        type: 'tree',
        position: { x: 200, y: 50 },
        data: {
          agentId,
          id: agentId,
          label: `Root Node ${this.nodes.filter(n => !this.edges.some(e => e.target === n.id)).length + 1}`,
          type: 'ROOT',
          meta: {
            type: 'LLM-Worker',
            is_leaf: false,
            weight: 1.0,
            description: 'Root node of the tree'
          },
          runtime: {
            is_alive: true,
            status_label: 'IDLE',
            last_seen_seconds_ago: 0,
            current_task: undefined,
            last_completed_task: undefined
          },
          visual: {
            statusColor: '#4ade80',
            statusIcon: '⏸️',
            progress: 0,
            timeElapsedMs: 0
          },
          childrenCount: 0,
          depth: 0
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

        const agentId = this.generateDataId();
        const newNode: Node<TreeNodeData> = {
          id: this.generateId(),
          type: 'tree',
          position: newPosition,
          data: {
            agentId,
            id: agentId,
            label: `Child Node ${this.nodes.filter(n => this.edges.some(e => e.source === parentId)).length + 1}`,
            type: 'CHILD',
            meta: {
              type: 'Search-Tool',
              is_leaf: false,
              weight: 0.8,
              description: 'Search tool agent'
            },
            runtime: {
              is_alive: true,
              status_label: 'IDLE',
              last_seen_seconds_ago: 0,
              current_task: undefined,
              last_completed_task: undefined
            },
            visual: {
              statusColor: '#4ade80',
              statusIcon: '⏸️',
              progress: 0,
              timeElapsedMs: 0
            },
            childrenCount: 0,
            depth: (parent.data?.depth || 0) + 1,
            parentId: parentId
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
        if (parent?.data) {
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
        if (parent?.data) {
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
      if (node?.data) {
        // 更新旧状态字段（向后兼容）
        node.data.status = status;
        
        // 更新新状态字段
        let statusLabel: 'IDLE' | 'BUSY' | 'OFFLINE';
        let statusColor: string;
        let statusIcon: string;
        
        switch (status) {
          case 'idle':
            statusLabel = 'IDLE';
            statusColor = '#4ade80';
            statusIcon = '⏸️';
            break;
          case 'running':
            statusLabel = 'BUSY';
            statusColor = '#FFA500';
            statusIcon = '🔄';
            break;
          case 'success':
            statusLabel = 'IDLE';
            statusColor = '#4ade80';
            statusIcon = '✅';
            break;
          case 'error':
          case 'killed':
            statusLabel = 'OFFLINE';
            statusColor = '#f43f5e';
            statusIcon = '🔴';
            break;
          default:
            statusLabel = 'IDLE';
            statusColor = '#4ade80';
            statusIcon = '⏸️';
        }
        
        node.data.runtime.status_label = statusLabel;
        node.data.visual.statusColor = statusColor;
        node.data.visual.statusIcon = statusIcon;
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