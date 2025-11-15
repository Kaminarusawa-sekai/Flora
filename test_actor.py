import asyncio
from new.agents.agent_actor import create_agent_actor

async def main():
    agent = await create_agent_actor(
        agent_id="test_agent_001",
        agent_name="测试智能体",
        max_concurrency=5
    )
    print(f"Agent created: {agent}")
    print(f"Agent ID: {agent.agent_id}")
    print(f"Agent Name: {agent.agent_name}")
    print(f"Max Concurrency: {agent.max_concurrency}")
    print(f"Parallel Executor: {agent.parallel_executor}")
    print(f"Task Coordinator: {agent.task_coordinator}")
    print(f"Tree Manager: {agent.tree_manager}")

if __name__ == "__main__":
    asyncio.run(main())