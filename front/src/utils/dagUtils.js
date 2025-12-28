/**
 * DAG 数据转换工具函数
 */

/**
 * 转换 trace 数据为前端 DAG 所需格式
 * @param {Object} traceData - 后端返回的 trace 数据
 * @returns {Object} 转换后的 DAG 数据
 */
export function transformTraceToDag(traceData) {
  // 构建 childrenCount 映射
  const childrenCountMap = {};
  traceData.edges.forEach(edge => {
    childrenCountMap[edge.source] = (childrenCountMap[edge.source] || 0) + 1;
  });

  // 根据状态获取进度
  const getProgressFromStatus = (status) => {
    const progressMap = {
      running: 50,
      success: 100,
      failed: 0,
      pending: 0,
      idle: 0
    };
    return progressMap[status] || 0;
  };

  // 根据状态获取颜色
  const getStatusColor = (status) => {
    const colorMap = {
      running: '#3b82f6', // 蓝色
      success: '#10b981', // 绿色
      failed: '#ef4444',   // 红色
      pending: '#f59e0b', // 黄色
      idle: '#6b7280'     // 灰色
    };
    return colorMap[status] || '#6b7280';
  };

  // 转换节点
  const nodes = traceData.nodes.map(node => ({
    id: node.id,
    type: 'glass',
    position: { x: 0, y: 0 }, // 暂时占位，后续用 dagre 自动布局
    data: {
      id: node.id,
      label: node.label,
      type: node.type,
      status: node.status,
      progress: getProgressFromStatus(node.status),
      time: 0, // 后端未提供，暂时设为0
      childrenCount: childrenCountMap[node.id] || 0
    }
  }));

  // 转换边
  const edges = traceData.edges.map((edge, index) => {
    const sourceNode = traceData.nodes.find(n => n.id === edge.source);
    const color = getStatusColor(sourceNode?.status || 'idle');
    return {
      id: `e-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      animated: sourceNode?.status === 'running',
      style: { stroke: color }
    };
  });

  return { nodes, edges };
}
