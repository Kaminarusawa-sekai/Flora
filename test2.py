# test_agent_actor.py
import time
from thespian.actors import ActorSystem
from agent.agent_actor import AgentActorThespian, TaskMessage, SubtaskResultMessage
from agent.config.agent_config_manager import AgentConfigManager

# 模拟依赖
class MockRegistry:
    def get_agent_by_id(self, aid):
        return {
            "agent_id": aid,
            "capabilities": ["book_flight"],
            "data_scope": {},
            "is_leaf": True
        }

def mock_fetch(query: str):
    return {"flight_id": "F123"}

def mock_execute(cap, ctx, mem):
    return f"Booked flight for {ctx.get('user', 'anon')}"

# 初始化全局配置
AgentConfigManager().set_global_config({
    "registry": MockRegistry(),
    "orchestrator": None,
    "data_resolver": None,
    "neo4j_recorder": None,
    "fetch_data_fn": mock_fetch,
    "acquire_resources_fn": lambda x: 1,
    "execute_capability_fn": mock_execute,
    "evaluator": lambda tid, res: 0.9,
    "improver": lambda tid, score: None,
})

def test_leaf_agent_with_db():
    with ActorSystem() as asys:
        agent = asys.createActor(AgentActorThespian)
        init_msg = AgentConfigManager().build_init_message("test-agent-1")
        asys.tell(agent, init_msg)

        # 发送任务
        task = TaskMessage("task-1", "book_flight", {"user": "alice"})
        asys.tell(agent, task)

        # 等待结果（最多 5 秒）
        start = time.time()
        while time.time() - start < 5:
            msg = asys.listen(1.0)
            if isinstance(msg, SubtaskResultMessage) and msg.task_id == "task-1":
                assert "Booked flight for alice" in str(msg.result)
                print("✅ Test passed!")
                return
        raise TimeoutError("No result received")