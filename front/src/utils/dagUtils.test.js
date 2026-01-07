import { transformTraceToDag } from './dagUtils.js';

// 测试数据
const testData = {
     "trace_id": "test-trace-f954a376", 
     "nodes": [ 
         { 
             "id": "root_test-trace-f954a376", 
             "label": "root_test-trace-f954a376", 
             "status": "PENDING", 
             "depth": 0, 
             "type": "customNode", 
             "signal": null 
         }, 
         { 
             "id": "test-trace-f954a376", 
             "label": "test-trace-f954a376", 
             "status": "RUNNING", 
             "depth": 1, 
             "type": "customNode", 
             "signal": null 
         }, 
         { 
             "id": "subtask-963cb605", 
             "label": "subtask-963cb605", 
             "status": "PENDING", 
             "depth": 2, 
             "type": "customNode", 
             "signal": null 
         }, 
         { 
             "id": "subtask-ae0fe993", 
             "label": "subtask-ae0fe993", 
             "status": "PENDING", 
             "depth": 2, 
             "type": "customNode", 
             "signal": null 
         } 
     ], 
     "edges": [ 
         { 
             "source": "root_test-trace-f954a376", 
             "target": "test-trace-f954a376" 
         }, 
         { 
             "source": "test-trace-f954a376", 
             "target": "subtask-963cb605" 
         }, 
         { 
             "source": "test-trace-f954a376", 
             "target": "subtask-ae0fe993" 
         } 
     ] 
 };

// 执行测试
console.log('=== DAG 转换测试 ===');
console.log('原始数据:', testData);

const result = transformTraceToDag(testData);

console.log('\n转换结果:');
console.log('节点:', result.nodes);
console.log('\n边:', result.edges);

// 验证结果
console.log('\n=== 结果验证 ===');
console.log(`节点数量: ${result.nodes.length} (预期: 4)`);
console.log(`边数量: ${result.edges.length} (预期: 3)`);

// 检查特定节点的转换
const runningNode = result.nodes.find(node => node.data.id === 'test-trace-f954a376');
console.log(`\n运行中节点转换结果:`);
console.log(`  状态: ${runningNode.data.status} (预期: RUNNING)`);
console.log(`  进度: ${runningNode.data.progress} (预期: 50)`);
console.log(`  子节点数量: ${runningNode.data.childrenCount} (预期: 2)`);

// 检查边的转换
const edge1 = result.edges.find(edge => edge.id === 'e-test-trace-f954a376-subtask-963cb605');
console.log(`\n边转换结果:`);
console.log(`  颜色: ${edge1.style.stroke} (预期: #3b82f6)`);
console.log(`  动画: ${edge1.animated} (预期: true)`);

console.log('\n=== 测试完成 ===');