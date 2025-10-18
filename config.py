# config.py

# Neo4j 配置（生产环境建议通过环境变量注入）
NEO4J_URI = "neo4j://121.36.203.36:7687"  # 注意：通常 Neo4j 使用 7687 端口（bolt 协议）
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "123456"

# 可选：未来可扩展其他配置
ACTOR_CLASS = "your_module.agent_actor.AgentActor"  # 如果需要动态导入
MAX_TASK_DURATION = 300
