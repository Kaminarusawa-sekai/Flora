# main.py

from fastapi import FastAPI, HTTPException, Header, Request, status
from pydantic import BaseModel
from typing import Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import uvicorn


from init_global_components import init_global_components
from config import NEO4J_URI, NEO4J_USER, CONNECTOR_RECORD_DB_URL


# ----------------------------
# 配置
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi-actor")



# 使用线程池处理阻塞的 Actor 操作（因为 FastAPI 是异步的）
executor = ThreadPoolExecutor(max_workers=20)



# ----------------------------
# 生命周期管理（优雅关闭）
# ----------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时（可选，你当前没有 startup 逻辑，所以留空或加日志）
    logger.info("Starting up application...")
    await init_global_components()
    yield  # 应用运行期间
    # 关闭时
    logger.info("Shutting down actors...")
    ActorManager.get_instance().stop_all()
    logger.info("Closing Neo4j connection...")
    registry = AgentRegistry.get_instance()
    registry.close()
    executor.shutdown(wait=True)
    logger.info("Shutdown complete.")


# ----------------------------
# FastAPI App
# ----------------------------

app = FastAPI(
    title="Agent Actor API",
    version="1.0",
    lifespan=lifespan  # 👈 关键：使用 lifespan 替代 on_event
)


class GenerateRequest(BaseModel):
    input: str  # 用户输入的一句话
    user_id: str  # 👈 注意：你路由中用了 request.user_id，所以 BaseModel 必须包含它！


class GenerateResponse(BaseModel):
    result: str
    agent_id: str
    task_id: str




def start_project():
    """
    启动整个项目
    包括初始化全局组件、启动FastAPI应用和RabbitMQ桥接器
    """
    import asyncio
    import threading
    
    # 1. 初始化全局组件
    asyncio.run(init_global_components())
    
    # 2. 启动RabbitMQ桥接器（在后台线程中运行）
    def start_rabbit_bridge_thread():
        try:
            start_rabbit_bridge()
        except Exception as e:
            logger.error(f"RabbitMQ bridge failed: {e}")
    
    rabbit_thread = threading.Thread(target=start_rabbit_bridge_thread, daemon=True)
    rabbit_thread.start()
    logger.info("RabbitMQ bridge started in background thread")
    
    # 3. 启动FastAPI应用
    logger.info("Starting FastAPI application...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_project()
    import thespian.actors as actors
    system = actors.ActorSystem("simpleSystemBase")
    from agents.agent_actor import AgentActor
    from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
    registry = AgentRegistry.get_instance(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD
    )

    connector_record = get_dify_registry(CONNECTOR_RECORD_DB_URL)
    # agent_id=registry.get_agent_id_by_user("tenant_001", "user_001")
    # mes=registry.get_agent_by_id(agent_id)
    # capabilities=registry.get_direct_children(agent_id)
    handler = system.createActor(AgentActor)
    from agent.message import InitMessage,TaskMessage,SubtaskErrorMessage
    init_msg = InitMessage(
        agent_id="private_domain",
        capabilities="做各类营销任务",           # Leaf: ["book_flight"]; Branch: ["route_flight"]
        memory_key = "private_domain",       # 默认 = agent_id
        registry=registry,

    )
    result = system.ask(handler, init_msg, timeout=1000)
    print("Final Result:", result)
    tsk_msg=TaskMessage(task_id="task_001", context={"帮我做下裂变活动": "裂变活动"})
    result = system.ask(handler, tsk_msg, timeout=1000)
    if isinstance(result,SubtaskErrorMessage ) or result is None:  # actor 退出
        from llm.qwen import QwenLLM
        llm=QwenLLM()
        resp=llm.generate("用户问了"+'{"帮我做下裂变活动": "裂变活动"}'+"，但是智能体崩溃了，你首先要尽可能根据用户的意图，生成一个最合适的回答用户，其再再判断一下是否需要就执行失败向用户道歉，如果需要你就向用户真诚的道歉。")
    print("Final Result:", result)

    system.shutdown()

