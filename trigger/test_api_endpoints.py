import requests
import json
import time
from uuid import uuid4

# API 基础 URL
base_url = "http://localhost:8000/api/v1"

# 生成唯一的测试名称
test_prefix = f"test_{uuid4().hex[:8]}"

def test_create_task_definition():
    """测试创建任务定义"""
    print("=== 测试创建任务定义 ===")
    url = f"{base_url}/definitions"
    payload = {
        "name": f"{test_prefix}_cron_task",
        "cron_expr": "* * * * *",
        "loop_config": {},
        "is_active": True
    }
    
    response = requests.post(url, json=payload)
    assert response.status_code == 200, f"创建任务定义失败: {response.status_code}"
    
    result = response.json()
    print(f"创建任务定义成功: {result['id']}")
    return result

def test_list_task_definitions():
    """测试获取任务定义列表"""
    print("\n=== 测试获取任务定义列表 ===")
    url = f"{base_url}/definitions"
    
    response = requests.get(url)
    assert response.status_code == 200, f"获取任务定义列表失败: {response.status_code}"
    
    result = response.json()
    print(f"获取到 {len(result)} 个任务定义")
    return result

def test_manual_trigger(def_id):
    """测试手动触发任务"""
    print(f"\n=== 测试手动触发任务 {def_id} ===")
    url = f"{base_url}/definitions/{def_id}/trigger"
    
    response = requests.post(url)
    assert response.status_code == 200, f"手动触发任务失败: {response.status_code}"
    
    result = response.json()
    print(f"手动触发任务成功: {result}")
    return result

def test_submit_adhoc_task(schedule_type, schedule_config=None):
    """测试提交即席任务"""
    print(f"\n=== 测试提交即席任务 (类型: {schedule_type}) ===")
    url = f"{base_url}/ad-hoc-tasks"
    
    payload = {
        "task_name": f"{test_prefix}_adhoc_{schedule_type.lower()}",
        "task_content": {"script": "print('hello')", "image": "python:3.9"},
        "input_params": {"test": "value"},
        "loop_config": {"max_rounds": 2, "interval_sec": 5},
        "is_temporary": True,
        "schedule_type": schedule_type
    }
    
    if schedule_config:
        payload["schedule_config"] = schedule_config
    
    response = requests.post(url, json=payload)
    assert response.status_code == 200, f"提交即席任务失败: {response.status_code}"
    
    result = response.json()
    print(f"提交即席任务成功: {result}")
    return result

def test_task_control(instance_id, action):
    """测试任务控制（取消、暂停、继续）"""
    print(f"\n=== 测试任务 {action} {instance_id} ===")
    url = f"{base_url}/instances/{instance_id}/{action}"
    
    response = requests.post(url)
    assert response.status_code == 200, f"任务 {action} 失败: {response.status_code}"
    
    result = response.json()
    print(f"任务 {action} 成功: {result}")
    return result

def test_task_modify(instance_id):
    """测试修改任务"""
    print(f"\n=== 测试修改任务 {instance_id} ===")
    url = f"{base_url}/instances/{instance_id}/modify"
    
    payload = {
        "input_params": {"test": "updated_value"},
        "schedule_config": {}
    }
    
    response = requests.patch(url, json=payload)
    assert response.status_code == 200, f"修改任务失败: {response.status_code}"
    
    result = response.json()
    print(f"修改任务成功: {result}")
    return result

def run_all_tests():
    """运行所有测试"""
    print("开始运行 API 端点测试...")
    print(f"测试前缀: {test_prefix}")
    
    # 记录测试结果
    test_results = {
        "create_task_definition": False,
        "list_task_definitions": False,
        "manual_trigger": False,
        "submit_adhoc_immediate": False,
        "submit_adhoc_cron": False,
        "submit_adhoc_delayed": False,
        "submit_adhoc_loop": False
    }
    
    try:
        # 1. 测试创建任务定义
        task_def = test_create_task_definition()
        assert "id" in task_def, "创建任务定义失败：返回结果中缺少 id 字段"
        def_id = task_def["id"]
        test_results["create_task_definition"] = True
        
        # 2. 测试获取任务定义列表
        task_defs = test_list_task_definitions()
        assert isinstance(task_defs, list), "获取任务定义列表失败：返回结果不是列表"
        test_results["list_task_definitions"] = True
        
        # 3. 测试手动触发任务
        trigger_result = test_manual_trigger(def_id)
        assert "status" in trigger_result, "手动触发任务失败：返回结果中缺少 status 字段"
        test_results["manual_trigger"] = True
        
        # 4. 测试提交各种类型的即席任务
        
        # 4.1 即时任务
        immediate_result = test_submit_adhoc_task("IMMEDIATE")
        assert "trace_id" in immediate_result, "提交即时任务失败：返回结果中缺少 trace_id 字段"
        assert immediate_result["status"] == "success", "提交即时任务失败：返回状态不是 success"
        test_results["submit_adhoc_immediate"] = True
        
        # 4.2 CRON 任务 (2025年12月24日20:00执行)
        cron_result = test_submit_adhoc_task(
            "CRON", 
            {"cron_expression": "0 20 24 12 *"}
        )
        assert "trace_id" in cron_result, "提交CRON任务失败：返回结果中缺少 trace_id 字段"
        assert cron_result["status"] == "success", "提交CRON任务失败：返回状态不是 success"
        test_results["submit_adhoc_cron"] = True
        
        # 4.3 DELAYED 任务
        delayed_result = test_submit_adhoc_task(
            "DELAYED",
            {"delay_seconds": 60}
        )
        assert "trace_id" in delayed_result, "提交DELAYED任务失败：返回结果中缺少 trace_id 字段"
        assert delayed_result["status"] == "success", "提交DELAYED任务失败：返回状态不是 success"
        test_results["submit_adhoc_delayed"] = True
        
        # 4.4 LOOP 任务
        loop_result = test_submit_adhoc_task("LOOP")
        assert "trace_id" in loop_result, "提交LOOP任务失败：返回结果中缺少 trace_id 字段"
        assert loop_result["status"] == "success", "提交LOOP任务失败：返回状态不是 success"
        test_results["submit_adhoc_loop"] = True
        
        # 5. 测试任务控制（使用即时任务的 trace_id 进行测试）
        # 注意：这里需要获取实际的 instance_id，可能需要从数据库查询
        # 由于当前测试环境限制，这里仅演示调用方式
        # if immediate_result.get("trace_id"):
        #     trace_id = immediate_result["trace_id"]
        #     # 测试取消任务
        #     cancel_result = test_task_control(instance_id, "cancel")
        #     assert cancel_result["success"], f"取消任务失败: {cancel_result['message']}"
        
        # 6. 输出测试结果摘要
        print("\n=== 测试结果摘要 ===")
        all_passed = True
        for test_name, passed in test_results.items():
            status = "✓ 成功" if passed else "✗ 失败"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        print("\n=== 所有测试完成 ===")
        if all_passed:
            print("🎉 API 端点测试全部通过！")
            return True
        else:
            print("❌ 部分测试失败，请检查日志！")
            return False
        
    except Exception as e:
        print(f"\n=== 测试失败 ===")
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    run_all_tests()
