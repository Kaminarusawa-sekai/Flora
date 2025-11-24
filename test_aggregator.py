#!/usr/bin/env python3
"""Test script for ResultAggregatorActor"""
from thespian.actors import ActorSystem
from new.agents.execution.result_aggregator import ResultAggregatorActor
import uuid
import time

def test_aggregator():
    """Test ResultAggregatorActor functionality"""
    asys = ActorSystem()
    
    try:
        # 创建聚合器
        aggregator = asys.createActor(ResultAggregatorActor)
        
        # 生成trace_id
        trace_id = str(uuid.uuid4())
        
        # 初始化聚合器
        asys.tell(aggregator, {
            "type": "initialize",
            "trace_id": trace_id,
            "max_retries": 3,
            "aggregation_strategy": "map_reduce"
        })
        
        # 添加子任务
        for i in range(5):
            asys.tell(aggregator, {
                "type": "add_subtask",
                "task_id": f"task_{i}",
                "trace_id": trace_id
            })
        
        # 发送4个成功结果
        for i in range(4):
            asys.tell(aggregator, {
                "type": "subtask_result",
                "task_id": f"task_{i}",
                "result": {
                    "success": True,
                    "output": f"result_{i}",
                    "task_id": f"task_{i}"
                },
                "trace_id": trace_id
            })
        
        # 发送1个错误结果
        asys.tell(aggregator, {
            "type": "subtask_error",
            "task_id": "task_4",
            "error": "Failed to execute task",
            "trace_id": trace_id
        })
        
        # 等待结果
        time.sleep(2)
        
        # 获取最终结果
        final_result = asys.ask(aggregator, {
            "type": "get_final_result",
            "trace_id": trace_id
        }, timeout=10)
        
        print("Final result:", final_result)
        
        # 验证结果
        assert final_result["type"] == "aggregation_complete"
        assert final_result["trace_id"] == trace_id
        assert len(final_result["completed_tasks"]) == 4
        assert len(final_result["failed_tasks"]) == 1
        assert final_result["aggregated_result"]["success"] == True
        assert final_result["aggregated_result"]["success_count"] == 4
        assert final_result["aggregated_result"]["failure_count"] == 1
        assert len(final_result["aggregated_result"]["aggregated_data"]) == 4
        
        print("✓ All tests passed!")
        
        return True
        
    finally:
        # 关闭Actor系统
        asys.shutdown()

if __name__ == "__main__":
    test_aggregator()
