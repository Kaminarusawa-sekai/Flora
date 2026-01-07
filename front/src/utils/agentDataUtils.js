/**
 * 用于将后端 Agent 数据转换为前端所需格式的工具函数
 */

/**
 * 从状态标签获取对应的颜色
 * @param {string} statusLabel - 状态标签：IDLE、BUSY、OFFLINE
 * @returns {string} 对应的颜色代码
 */
function getStatusColor(statusLabel) {
  switch (statusLabel) {
    case 'IDLE':
      return '#4ade80';
    case 'BUSY':
      return '#FFA500';
    case 'OFFLINE':
      return '#f43f5e';
    default:
      return '#4ade80';
  }
}

/**
 * 从状态标签获取对应的图标
 * @param {string} statusLabel - 状态标签：IDLE、BUSY、OFFLINE
 * @returns {string} 对应的图标
 */
function getStatusIcon(statusLabel) {
  switch (statusLabel) {
    case 'IDLE':
      return '⏸️';
    case 'BUSY':
      return '🔄';
    case 'OFFLINE':
      return '🔴';
    default:
      return '⏸️';
  }
}

/**
 * 计算节点的位置
 * @param {number} index - 节点在同级中的索引
 * @param {number} totalSiblings - 同级节点总数
 * @param {number} parentX - 父节点X坐标
 * @param {number} parentY - 父节点Y坐标
 * @param {number} depth - 当前节点深度
 * @returns {{x: number, y: number}} 计算出的位置
 */
function calculateNodePosition(index, totalSiblings, parentX, parentY, depth) {
  const verticalSpacing = 400;
  const horizontalSpacing = 400;
  
  // 计算水平偏移量，使子节点均匀分布在父节点下方
  const offset = (totalSiblings - 1) * horizontalSpacing / 2;
  const x = parentX + (index * horizontalSpacing) - offset;
  const y = parentY + verticalSpacing;
  
  return { x, y };
}

/**
 * 将后端Agent数据映射为前端NodeData结构
 * @param {Object} agent - 后端Agent数据
 * @param {number} x - 节点X坐标
 * @param {number} y - 节点Y坐标
 * @param {number} depth - 节点深度
 * @param {string} parentId - 父节点ID
 * @returns {Object} 前端NodeData结构
 */
function mapToNodeData(agent, x, y, depth = 0, parentId = null) {
  // 使用可选链和默认值确保数据完整性
  const { agent_id, meta = {}, runtime_state = {}, children = [] } = agent;
  
  return {
    agentId: agent_id,
    id: agent_id,
    label: meta.name || 'Unnamed',
    type: meta.type || 'Unknown',
    meta: {
      type: meta.type || 'Unknown',
      is_leaf: meta.is_leaf ?? false,
      weight: meta.weight ?? 0,
      description: meta.description || ''
    },
    runtime: {
      is_alive: runtime_state.is_alive ?? false,
      status_label: runtime_state.status_label || 'UNKNOWN',
      last_seen_seconds_ago: runtime_state.last_seen_seconds_ago ?? 0,
      current_task: runtime_state.current_task ? {
        task_id: runtime_state.current_task.task_id,
        trace_id: runtime_state.current_task.trace_id,
        step: runtime_state.current_task.step,
        reported_at: runtime_state.current_task.reported_at
      } : undefined,
      last_completed_task: runtime_state.last_completed_task ? {
        task_id: runtime_state.last_completed_task.task_id,
        status: runtime_state.last_completed_task.status,
        end_time: runtime_state.last_completed_task.end_time,
        duration: runtime_state.last_completed_task.duration
      } : undefined
    },
    visual: {
      progress: null, // 如果有进度信息可以从runtime或meta中获取
      timeElapsedMs: 0, // 如果有时间信息可以从runtime或meta中获取
      statusColor: getStatusColor(runtime_state.status_label || 'UNKNOWN'),
      statusIcon: getStatusIcon(runtime_state.status_label || 'UNKNOWN')
    },
    childrenCount: children.length,
    depth: depth,
    parentId: parentId,
    traceId: runtime_state.current_task?.trace_id || '',
    position: { x, y }
  };
}

/**
 * 递归处理树形结构，计算所有节点的位置和深度
 * @param {Object} agentTree - 后端Agent树数据
 * @param {number} rootX - 根节点X坐标
 * @param {number} rootY - 根节点Y坐标
 * @returns {{nodes: Array, edges: Array}} 前端节点和边数据
 */
function processAgentTree(agentTree, rootX = 200, rootY = 50) {
  const nodes = [];
  const edges = [];
  
  // 递归处理节点
  function recursiveProcess(agent, parentPosition, depth, parentId = null) {
    const { x, y } = parentPosition;
    
    // 创建前端节点
    const nodeId = `node-${agent.agent_id}`;
    const node = mapToNodeData(agent, x, y, depth, parentId);
    nodes.push({
      id: nodeId,
      type: 'tree',
      position: { x, y },
      data: node
    });
    
    // 如果有父节点，创建边
    if (parentId) {
      edges.push({
        id: `e${parentId}-${nodeId}`,
        source: parentId,
        target: nodeId,
        animated: true,
        style: { stroke: '#4ade80' }
      });
    }
    
    // 处理子节点
    const children = agent.children || [];
    children.forEach((child, index) => {
      const childPosition = calculateNodePosition(
        index,
        children.length,
        x,
        y,
        depth + 1
      );
      recursiveProcess(child, childPosition, depth + 1, nodeId);
    });
  }
  
  // 开始处理根节点
  recursiveProcess(agentTree, { x: rootX, y: rootY }, 0);
  
  return { nodes, edges };
}

export {
  mapToNodeData,
  processAgentTree,
  getStatusColor,
  getStatusIcon
};
