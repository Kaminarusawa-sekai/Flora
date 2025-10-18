# agent/config/agent_config_manager.py
import threading
from typing import Dict, Any, Callable
from agent.message import InitMessage

class AgentConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._config = {}
        return cls._instance

    def set_global_config(self, config: Dict[str, Any]):
        """一次性设置全局共享依赖"""
        self._config = config

    def build_init_message(self, agent_id: str) -> dict:
        agent_meta = self._config["registry"].get_agent_by_id(agent_id)
    
     # 从 Neo4j 动态加载 dispatch_rules（如果是 Branch）
        dispatch_rules = {}
        if not agent_meta.get("is_leaf", False):
            dispatch_rules = self._config["neo4j_recorder"].load_dispatch_rules(agent_id)

        return InitMessage(
            agent_id=agent_id,
            is_leaf=agent_meta.get("is_leaf", True),
            capabilities=agent_meta["capabilities"],
            dispatch_rules=dispatch_rules,
            memory_key=agent_id,  # 或自定义
            optimization_interval=self._config.get("optimization_interval", 3600),
            # 注入依赖
            registry=self._config["registry"],
            fetch_data_fn=self._config["fetch_data_fn"],
            execute_capability_fn=self._config["execute_capability_fn"],
            neo4j_recorder=self._config["neo4j_recorder"],
            # "type": "init",
            # "agent_id": agent_id,
            # "registry": self._config["registry"],
            # "orchestrator": self._config["orchestrator"],
            # "data_resolver": self._config["data_resolver"],
            # "neo4j_recorder": self._config["neo4j_recorder"],
            # "fetch_data_fn": self._config["fetch_data_fn"],
            # "acquire_resources_fn": self._config["acquire_resources_fn"],
            # "execute_capability_fn": self._config["execute_capability_fn"],
            # "execute_self_capability_fn": self._config.get("execute_self_capability_fn"),
            # "evaluator": self._config["evaluator"],
            # "improver": self._config["improver"],
            # "optimization_interval": self._config.get("optimization_interval", 3600),
        )
