# main.py

from fastapi import FastAPI, HTTPException, Header, Request, status
from pydantic import BaseModel
from typing import Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import uvicorn

from agent.agent_registry import AgentRegistry
from actor_manager.actor_manager import ActorManager
from agent.agent_actor import AgentActor
from task_orchestrator.orchestrator import TaskOrchestrator
from task_orchestrator.context import current_tenant_id, current_user_id
from init_global_components import init_global_components
from connector.dify_connector import DifyRunRegistry, DifyRunRecord, get_dify_registry
from config import NEO4J_URI, NEO4J_USER, CONNECTOR_RECORD_DB_URL


# ----------------------------
# 配置
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastapi-actor")



# registry = AgentRegistry(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
# actor_manager = ActorManager(registry=registry, actor_class=AgentActor)
# orchestrator = TaskOrchestrator(registry)

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


# ----------------------------
# 工具函数
# ----------------------------

# def route_and_execute(tenant_id: str,user_id:str, user_input: str) -> dict:
#     """
#     核心逻辑：根据用户输入，找到根智能体，发送任务，等待结果。
#     注意：此函数是阻塞的，应在 executor 中运行。
#     """
#     # 1. 获取根智能体（假设系统中有一个固定的入口 agent，如 "root_router"）
#     root_agent_id = "root_router"  # 👈 你需要在 Neo4j 中预先注册这个 agent

#     # 2. 获取或创建该租户的 root actor
#     try:
#         actor = actor_manager.get_or_create_actor(
#             tenant_id=tenant_id,
#             agent_id=root_agent_id,
#             orchestrator_callback=None  # 可选：用于调试
#         )
#     except ValueError as e:
#         raise RuntimeError(f"Root agent not found in registry: {e}")

#     # 3. 构造任务消息
#     task_id = f"task_{hash(user_input) % 1000000}"
#     message = {
#         "task_id": task_id,
#         "capability": "generate",  # 假设根智能体支持 "generate"
#         "context": {
#             "user_input": user_input,
#             "tenant_id": tenant_id,
#             # 其他上下文可扩展
#         }
#     }

#     # 4. 发送消息并等待结果（需 AgentActor 支持同步返回或回调）
#     # 👇 这里假设 AgentActor 有一个 `.execute_sync(message)` 方法
#     # 如果你当前是纯异步/回调模式，需要改造为支持 Future 或 Queue
#     try:
#         result = actor.execute_sync(message)  # ← 关键：你需要实现这个方法
#         return {
#             "result": result.get("output", ""),
#             "agent_id": result.get("handled_by", root_agent_id),
#             "task_id": task_id
#         }
#     except Exception as e:
#         logger.error(f"Execution failed: {e}")
#         raise RuntimeError(f"Agent execution error: {e}")

def submit_task(self, agent_id, capability, context):
    root_actor = self.asys.createActor(AgentActorThespian)
    init_msg = build_init(agent_id, ...)
    self.asys.tell(root_actor, init_msg)
    task_msg = TaskMessage(frame_id="root", capability=capability, context=context)
    self.asys.tell(root_actor, task_msg)
    # 后续结果直接发给用户或回调地址，不经过 Orchestrator



# ----------------------------
# 路由
# ----------------------------
##TODO:用户和节点的对应还没添加
@app.post("/generate")
async def generate(
    request: GenerateRequest,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID")
):
    user_input = request.input.strip()
    user_id = request.user_id.strip()
    if not user_input or not user_id:
        raise HTTPException(400, "input and user_id are required")

    # 1. 根据 user_id + tenant_id 找到对应的 agent_id
    agent_id = AgentRegistry.get_instance().get_agent_id_by_user(x_tenant_id, user_id)

    if not agent_id:
        raise HTTPException(404, f"No agent assigned to user '{user_id}' in tenant '{x_tenant_id}'")

    # # 2. 获取或创建该用户的 Actor（属于该租户）
    # actor = actor_manager.get_or_create_actor(
    #     tenant_id=x_tenant_id,
    #     agent_id=agent_id,
    #     # orchestrator_callback 已由 manager 统一注入
    # )

    # # 3. 生成唯一 frame_id
    # frame_id = f"frame_{x_tenant_id}_{user_id}_{hash(user_input) % 1000000}"

    # # 4. 注册 Future 监听结果
    # future = orchestrator.register_future_for_frame(frame_id)

    # # 5. 触发任务（异步非阻塞）
    # actor.handle_task(
    #     frame_id=frame_id,
    #     capability="generate",  # 或根据输入动态决定
    #     context={
    #         "user_input": user_input,
    #         "user_id": user_id,
    #         "tenant_id": x_tenant_id,
    #         # 其他上下文
    #     }
    # )

    # # 6. 等待结果（带超时）
    # try:
    #     result = await asyncio.wait_for(future, timeout=30.0)
    # except asyncio.TimeoutError:
    #     raise HTTPException(504, "Agent execution timeout")

    # if result["status"] == "error":
    #     raise HTTPException(500, f"Agent error: {result['error']}")

    # return {
    #     "result": result["result"],
    #     "agent_id": agent_id,
    #     "frame_id": frame_id
    # }
    # 设置租户/用户上下文（与 task 无关，但可用于日志/权限）
    tenant_token = current_tenant_id.set(x_tenant_id)
    user_token = current_user_id.set(user_id)

    # Orchestrator 现在极简：

    try:
        # 1. 提交任务（返回 task_id）

        orchestrator = await TaskOrchestrator.get_instance()
        task_id = await orchestrator.submit_task(
            entry_agent_id=agent_id,  # 👈 根 Agent
            capability="generate",            # 👈 根能力（可固定或传入）
            initial_context={
                "prompt": user_input,
                "user_id": user_id,
                "tenant_id": x_tenant_id,     # 显式传入，便于子帧继承
            },
            tenant_id=x_tenant_id,            # 用于 Actor 路由
        )

        # 2. 等待整个任务完成（所有帧）
        try:
            all_results = await asyncio.wait_for(
                orchestrator.get_task_done_future(task_id),
                timeout=30.0
            )
            # all_results: List[Dict]，每个包含 frame_id, result/error, status 等
            return {"task_id": task_id, "results": all_results}

        except asyncio.TimeoutError:
            # 可选：触发取消逻辑
            await orchestrator.cancel_task(task_id)
            raise HTTPException(status_code=504, detail="Task timeout")

    finally:
        # 清理上下文
        current_tenant_id.reset(tenant_token)
        current_user_id.reset(user_token)



#dify 回调接口
@app.post("/dify-callback")
async def dify_callback(request: Request):
    payload = await request.json()
    run_id = payload.get("workflow_run_id")
    status = payload.get("status", "unknown")
    outputs = payload.get("outputs")

    # 1. 获取任务信息
    result = dify_registry.get_run(run_id)
    if not result:
        return {"error": "run_id not found"}
    
    task_id, original_sender, _ = result

    # 2. 更新状态
    dify_registry.complete_run(run_id, status, outputs)

    # 3. 通知 Actor
    if status == "succeeded":
        msg = SubtaskResultMessage(task_id, outputs)
    else:
        msg = SubtaskErrorMessage(task_id, f"Dify failed: {status}")

    actor_system.tell(original_sender, msg)
    return {"status": "notified"}




# 全局 ActorSystem 和 Observer 引用
# asys: ActorSystem = None
# observer_ref = None

# @app.on_event("startup")
# async def startup_event():
#     global asys, observer_ref
#     asys = ActorSystem('multiprocTCPBase')
#     observer_ref = asys.createActor(TaskObserver)

# @app.on_event("shutdown")
# async def shutdown_event():
#     global asys
#     if asys:
#         asys.shutdown()

# @app.get("/tasks/active")
# async def get_active_tasks() -> Dict[str, Any]:
#     global asys, observer_ref
#     if not observer_ref:
#         return {"error": "Observer not initialized"}
#     response = asys.ask(observer_ref, {"query": "active_tasks"}, timeout=2)
#     return response

# @app.get("/tasks/history")
# async def get_task_history() -> Dict[str, Any]:
#     global asys, observer_ref
#     if not observer_ref:
#         return {"error": "Observer not initialized"}
#     response = asys.ask(observer_ref, {"query": "task_history"}, timeout=2)
#     return response

# # 用于获取 observer_ref 注入到 AgentActor
# def get_observer_ref():
#     return observer_ref

async def test():
    # await generate(GenerateRequest(input="hello", user_id="1"))
    import thespian.actors as actors
    system = actors.ActorSystem("simpleSystemBase")

    handler = system.createActor(DataActor)


if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    # asyncio.run(init_global_components())
    # asyncio.run(test())
    import thespian.actors as actors
    system = actors.ActorSystem("simpleSystemBase")
    from agent.agent_actor import AgentActor
    from agent.agent_registry import AgentRegistry
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

