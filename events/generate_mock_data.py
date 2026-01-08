import asyncio
import json
import random
from datetime import datetime, timedelta
from external.db.base import AgentTaskHistoryRepository, AgentDailyMetricRepository
from external.db.impl.sqlite_impl import SQLiteAgentTaskHistoryRepository, SQLiteAgentDailyMetricRepository
from external.db.session import async_session, create_tables

# 节点列表
task_nodes = {
    "rules_system_create_active": "规则与系统构建-新增活动",
    "rules_system_create_active_center": "规则与系统构建-新增活动中心",
    "private_domain": "私域营销",
    "fission_activity": "裂变活动策划",
    "fission_implement": "裂变实施",
    "fission_mech_design": "裂变机制设计",
    "user_strat_fission": "用户分层裂变设计",
    "activity_creative": "活动创意与立项",
    "def_planning": "定义与规划",
    "fission_user_portrait": "裂变用户分层与画像定义",
    "mech_game_design": "机制与玩法设计",
    "rules_system": "规则与系统构建",
    "strat_fission_strat": "分层裂变策略设计",
    "comm_scripts": "定制沟通话术与素材",
    "copy_planning": "文案策划",
    "fission_game_match": "匹配裂变玩法",
    "gameplay_mode": "玩法模式选择",
    "goal_setting": "目标设定",
    "incentive_system": "激励体系设计",
    "strat_incentives": "设计分层激励",
    "strat_portraits": "绘制分层画像"
}

# 模拟agent_id列表 - 使用task_nodes的键作为agent_id
agent_ids = list(task_nodes.keys())

# 状态列表
status_list = ["COMPLETED", "FAILED", "CANCELLED"]

async def generate_mock_data():
    """生成模拟数据并插入到数据库中"""
    # 使用现有的建表函数
    await create_tables()
    
    # 使用现有的异步会话工厂
    async with async_session() as session:
        # 创建仓库实例，传递session参数
        task_history_repo = SQLiteAgentTaskHistoryRepository(session)
        daily_metric_repo = SQLiteAgentDailyMetricRepository(session)
        
        # 生成最近30天的模拟数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        current_date = start_date
        while current_date <= end_date:
            # 为每个agent生成每天的模拟数据
            for agent_id in agent_ids:
                # 每天生成3-10个任务
                task_count = random.randint(3, 10)
                
                for i in range(task_count):
                    # 随机选择一个节点
                    task_key = random.choice(list(task_nodes.keys()))
                    task_name = task_nodes[task_key]
                    
                    # 随机生成任务时间
                    task_start_time = current_date + timedelta(
                        hours=random.randint(9, 17),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )
                    
                    # 随机生成任务持续时间（1-30分钟）
                    duration_seconds = random.randint(60, 1800)
                    task_end_time = task_start_time + timedelta(seconds=duration_seconds)
                    duration_ms = duration_seconds * 1000
                    
                    # 随机生成状态
                    status = random.choice(status_list)
                    
                    # 生成trace_id和task_id
                    trace_id = f"trace_{random.randint(100000, 999999)}"
                    task_id = f"task_{random.randint(100000, 999999)}"
                    
                    # 生成模拟输入参数和输出结果
                    input_params = {
                        "node_type": task_key,
                        "node_name": task_name,
                        "some_param": random.randint(1, 100)
                    }
                    
                    output_result = {
                        "result": f"Successfully processed {task_name}",
                        "metrics": {
                            "processed_items": random.randint(10, 1000),
                            "accuracy": round(random.uniform(0.8, 1.0), 2)
                        }
                    }
                    
                    # 生成错误信息（如果任务失败）
                    error_msg = None
                    if status == "FAILED":
                        error_msg = f"Error processing {task_name}: Some random error occurred"
                    
                    # 创建任务历史记录
                    task_history = {
                        "agent_id": agent_id,
                        "trace_id": trace_id,
                        "task_id": task_id,
                        "task_name": task_name,
                        "status": status,
                        "start_time": task_start_time,
                        "end_time": task_end_time,
                        "duration_ms": duration_ms,
                        "input_params": input_params,
                        "output_result": output_result,
                        "error_msg": error_msg
                    }
                    
                    # 插入任务历史记录
                    await task_history_repo.create(task_history)
                    
                    # 更新每日指标
                    await daily_metric_repo.update_daily_metric(
                        agent_id=agent_id,
                        date_str=current_date.strftime("%Y-%m-%d"),
                        status=status,
                        duration_ms=duration_ms
                    )
            
            # 移动到下一天
            current_date += timedelta(days=1)
        
        # 提交事务
        await session.commit()
    
    print(f"模拟数据生成完成！已生成{len(agent_ids)}个Agent，30天的数据，每天3-10个任务。")

if __name__ == "__main__":
    asyncio.run(generate_mock_data())
