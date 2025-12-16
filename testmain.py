import logging
from thespian.actors import ActorSystem
from datetime import datetime
import uuid

# 假设你的模块路径如下，请根据实际结构调整
from tasks.agents.agent_actor import AgentActor
from tasks.common.messages import AgentTaskMessage
from tasks.capabilities import get_capability_manager, init_capabilities

# 设置日志（可选）
logging.basicConfig(level=logging.INFO)

def main():
    # 创建本地 Actor 系统（使用 simpleSystemBase，适合测试）
    asys = ActorSystem("simpleSystemBase")
        # 初始化能力管理器
    init_capabilities()

    try:
        # 创建 AgentActor 实例
        agent_addr = asys.createActor(AgentActor)

        # 构造任务消息
        task_msg = AgentTaskMessage(
            agent_id="private_domain",
            task_id=str(uuid.uuid4()),
            user_id="<user_id:1>,<tenant_id:1>",
            content="帮设定一下裂变目标，我是做投影仪的",
            description="设定裂变目标任务",
            trace_id=str(uuid.uuid4()),
            task_path="/",
            reply_to=None,  # 回复将由系统自动路由回本进程（在 simpleSystem 中）
        )

        print(f"Sending task to AgentActor: {task_msg.task_id}")
        
        # 发送消息
        asys.tell(agent_addr, task_msg)

        # 等待几秒让 Actor 处理（simpleSystem 是同步的，通常立即完成）
        import time
        time.sleep(200)

        print("Task message sent. Check logs for processing details.")

    finally:
        # 关闭 Actor 系统
        asys.shutdown()

if __name__ == "__main__":
    main()