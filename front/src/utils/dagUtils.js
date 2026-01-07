/**
 * DAG 数据转换工具函数
 */
import dagre from 'dagre';

// 配置项：定义节点的大致宽高，帮助算法计算间距
// 与 GlassNode.vue 中的实际尺寸保持一致
const NODE_WIDTH = 280;
const NODE_HEIGHT = 200;

/**
 * 转换 trace 数据为前端 DAG 所需格式
 * @param {Object} traceData - 后端返回的 trace 数据
 * @returns {Object} 转换后的 DAG 数据
 */
export function transformTraceToDag(traceData, direction = 'TB') {
  // 1. 初始化 dagre 图形实例
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // 设置布局方向：'TB' (Top to Bottom) 垂直布局, 'LR' (Left to Right) 水平布局
  dagreGraph.setGraph({ rankdir: direction });

  // --- 原有的辅助函数 (保持不变) ---
  const childrenCountMap = {};
  traceData.edges.forEach(edge => {
    childrenCountMap[edge.source] = (childrenCountMap[edge.source] || 0) + 1;
  });

  const getProgressFromStatus = (status) => {
    const progressMap = { running: 50, success: 100, failed: 0, pending: 0, idle: 0 };
    return progressMap[status.toLowerCase()] || 0;
  };

  const getStatusColor = (status) => {
    const colorMap = {
      running: '#3b82f6', success: '#10b981', failed: '#ef4444',
      pending: '#f59e0b', idle: '#6b7280'
    };
    return colorMap[status.toLowerCase()] || '#6b7280';
  };
  // ----------------------------------

  // 2. 准备节点数据 (先不设置 position)
  const rawNodes = traceData.nodes.map(node => ({
    id: node.id,
    type: 'glass',
    data: {
      id: node.id,
      label: node.label,
      type: node.type,
      status: node.status,
      progress: getProgressFromStatus(node.status),
      time: 0,
      childrenCount: childrenCountMap[node.id] || 0
    }
  }));

  // 3. 将节点和边注册到 dagre 中
  rawNodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  traceData.edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // 4. 执行布局计算
  dagre.layout(dagreGraph);

  // 5. 将计算好的坐标回填给节点
  // 注意：dagre 返回的是中心点 (x, y)，通常流图库(如 ReactFlow)需要左上角坐标
  const layoutedNodes = rawNodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  // 6. 转换边 (保持原逻辑)
  const edges = traceData.edges.map((edge) => {
    const sourceNode = traceData.nodes.find(n => n.id === edge.source);
    const color = getStatusColor(sourceNode?.status || 'idle');
    return {
      id: `e-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      animated: sourceNode?.status?.toLowerCase() === 'running',
      style: { stroke: color }
    };
  });

  return { nodes: layoutedNodes, edges };
}