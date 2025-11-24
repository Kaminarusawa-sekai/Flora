#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试并行任务聚合器
"""

import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入需要测试的模块
from new.capability_actors.parallel_task_aggregator_actor import ParallelTaskAggregatorActor
from new.common.messages.task_messages import RepeatTaskRequest, TaskSpec

def test_parallel_task_aggregator_import():
    """
    测试并行任务聚合器的导入
    """
    print("=== 测试并行任务聚合器导入 ===")
    
    try:
        # 创建任务规范
        task_spec = TaskSpec(
            task_id="test_parallel_task",
            type="dify",
            parameters={"content": "Test parallel task"},
            repeat_count=3,
            aggregation_strategy="list"
        )
        print(f"✓ 创建任务规范成功: {task_spec}")
        print(f"  - repeat_count: {task_spec.repeat_count}")
        print(f"  - aggregation_strategy: {task_spec.aggregation_strategy}")
        print(f"  - parameters: {task_spec.parameters}")
        
        # 创建重复任务请求
        request = RepeatTaskRequest(
            source="test_source",
            destination="test_dest",
            spec=task_spec,
            reply_to="test_reply"
        )
        print(f"✓ 创建重复任务请求成功: {request}")
        
        print("=== 测试完成 ===")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_parallel_task_aggregator_import()
