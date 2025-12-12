#!/usr/bin/env python3
"""
任务中台服务使用示例
"""
from datetime import datetime, timedelta
from events.task_control_service import task_control_service
from events.task_models import TaskTriggerType, TaskStatus

def example_immediate_task():
    """示例：立即执行任务"""
    print("=== 示例1: 立即执行任务 ===")
    task_def_id = task_control_service.create_task(
        user_id="user1",
        content="立即执行的测试任务",
        trigger_type=TaskTriggerType.IMMEDIATE
    )
    print(f"创建的任务ID: {task_def_id}")
    print("任务已立即执行")
    return task_def_id

def example_scheduled_task():
    """示例：定时执行任务"""
    print("\n=== 示例2: 定时执行任务 ===")
    # 设置10秒后执行
    run_date = datetime.now() + timedelta(seconds=10)
    task_def_id = task_control_service.create_task(
        user_id="user1",
        content="定时执行的测试任务",
        trigger_type=TaskTriggerType.SCHEDULED,
        trigger_args={"run_date": run_date}
    )
    print(f"创建的任务ID: {task_def_id}")
    print(f"任务将在 {run_date.strftime('%Y-%m-%d %H:%M:%S')} 执行")
    return task_def_id

def example_loop_task():
    """示例：循环执行任务"""
    print("\n=== 示例3: 循环执行任务 ===")
    task_def_id = task_control_service.create_task(
        user_id="user1",
        content="循环执行的测试任务",
        trigger_type=TaskTriggerType.LOOP,
        trigger_args={"interval": 30}  # 每30秒执行一次
    )
    print(f"创建的任务ID: {task_def_id}")
    print("任务将每30秒执行一次")
    return task_def_id

def example_operations(task_def_id):
    """示例：任务操作"""
    print(f"\n=== 示例4: 任务操作 ===")
    print(f"操作对象: {task_def_id}")
    
    # 获取任务定义
    task_def = task_control_service.get_task_definition(task_def_id)
    print(f"当前任务状态: {task_def.status}")
    
    # 暂停任务
    task_control_service.pause_schedule(task_def_id)
    task_def = task_control_service.get_task_definition(task_def_id)
    print(f"暂停后任务状态: {task_def.status}")
    
    # 手动触发
    print("手动触发一次任务...")
    task_control_service.trigger_immediately(task_def_id)
    
    # 恢复任务
    task_control_service.resume_schedule(task_def_id)
    task_def = task_control_service.get_task_definition(task_def_id)
    print(f"恢复后任务状态: {task_def.status}")
    
    # 查看任务实例
    instances = task_control_service.get_task_instances(task_def_id)
    print(f"任务实例数量: {len(instances)}")
    for instance in instances[:3]:  # 只显示前3个
        print(f"  - 实例ID: {instance.instance_id}, 状态: {instance.status}, 创建时间: {instance.created_at}")
    
    # 取消任务
    # task_control_service.cancel_task(task_def_id)
    # task_def = task_control_service.get_task_definition(task_def_id)
    # print(f"取消后任务状态: {task_def.status}")

def main():
    """主函数"""
    print("任务中台服务使用示例")
    print("=" * 50)
    
    # 创建各种类型的任务
    # immediate_task_id = example_immediate_task()
    # scheduled_task_id = example_scheduled_task()
    loop_task_id = example_loop_task()
    
    # 执行任务操作
    example_operations(loop_task_id)
    
    print("\n=== 示例结束 ===")
    print("任务将继续运行，按 Ctrl+C 终止")
    
    try:
        # 保持程序运行，观察任务执行
        while True:
            pass
    except KeyboardInterrupt:
        print("\n程序终止")
        # 清理测试任务
        task_control_service.cancel_task(loop_task_id)
        # task_control_service.cancel_task(scheduled_task_id)
        # task_control_service.cancel_task(immediate_task_id)
        print("测试任务已清理")

if __name__ == "__main__":
    main()