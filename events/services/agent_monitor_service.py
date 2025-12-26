import json
import time
from typing import Dict, List, Any, Optional
from external.cache.base import CacheClient
from external.client.agent_client import AgentClient

class AgentMonitorService:
    def __init__(self, cache: CacheClient, agent_client: Optional[AgentClient] = None):
        self.cache = cache
        self.agent_client = agent_client if agent_client is not None else AgentClient()
        self.PREFIX = "agent:state:"
        self.TTL = 300  # 5分钟无心跳视为"死掉了"

    def _key(self, agent_id: str) -> str:
        return f"{self.PREFIX}{agent_id}"

    async def report_heartbeat(self, agent_id: str, task_info: dict):
        """
        Worker 上报心跳：我活着，我正在做 task_info
        """
        key = self._key(agent_id)
        state = {
            "last_seen": time.time(),
            "status": "BUSY" if task_info else "IDLE", # 有任务就是忙，没任务且活着就是闲
            "current_task": task_info, # {trace_id: xxx, task_id: xxx, step: xxx}
            "meta": {} # 可以放 CPU/内存等信息
        }
        # 存入 Redis，有效期 5 分钟
        await self.cache.set(key, json.dumps(state), ex=self.TTL)

    async def get_agents_status_map(self, agent_ids: List[str]) -> Dict[str, dict]:
        """
        批量获取 Agent 的状态
        """
        if not agent_ids:
            return {}
            
        keys = [self._key(aid) for aid in agent_ids]
        # 假设 cache.mget 支持批量获取，这是性能关键点
        # 如果不支持，需要用循环 await self.cache.get(k)
        raw_values = await self.cache.mget(keys)
        
        result = {}
        current_time = time.time()
        
        for agent_id, raw_val in zip(agent_ids, raw_values):
            if not raw_val:
                # Redis 里没有 key，说明过期了或者从未上线 -> 判定为 DEAD
                result[agent_id] = {
                    "is_alive": False,
                    "status_label": "OFFLINE",
                    "last_seen_seconds_ago": None,
                    "current_task": None
                }
            else:
                data = json.loads(raw_val)
                last_seen = data.get("last_seen", 0)
                # 双重校验：虽然 Key 有 TTL，但这里可以计算具体离线多久
                time_diff = current_time - last_seen
                
                result[agent_id] = {
                    "is_alive": True,
                    "status_label": data.get("status", "IDLE"),
                    "last_seen_seconds_ago": int(time_diff),
                    "current_task": data.get("current_task")
                }
        return result

    async def enrich_subtree_with_status(self, subtree_root: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心方法：接收静态树，返回带状态的动态树
        """
        # 1. 扁平化收集树中所有的 agent_id
        all_agent_ids = []
        def collect_ids(node):
            if "agent_id" in node:
                all_agent_ids.append(node["agent_id"])
            for child in node.get("children", []):
                collect_ids(child)
        
        collect_ids(subtree_root)
        
        # 2. 批量查询 Redis 状态 (一次网络 IO)
        status_map = await self.get_agents_status_map(all_agent_ids)
        
        # 3. 递归回填状态到树节点中
        def inject_status(node):
            aid = node.get("agent_id")
            if aid in status_map:
                # 将状态注入到节点数据中，建议放在一个新的 runtime 字段下，不污染 meta
                node["runtime_state"] = status_map[aid]
            else:
                # 兜底
                node["runtime_state"] = {"is_alive": False, "status_label": "UNKNOWN"}
            
            # 递归处理子节点
            for child in node.get("children", []):
                inject_status(child)
            return node

        return inject_status(subtree_root)

    async def get_static_agent_tree(self, agent_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的静态Agent子树

        Args:
            agent_id: 根节点Agent ID

        Returns:
            静态子树结构，格式如下：
            {
                "agent_id": str,              # 节点Agent ID
                "meta": {                     # 节点元数据
                    "name": str,              # Agent名称
                    "type": str,              # Agent类型
                    "is_leaf": bool,          # 是否为叶子节点
                    "weight": float,          # 权重值
                    "description": str        # 描述信息
                    # 其他元数据字段...
                },
                "children": [                 # 子节点列表（递归结构）
                    {
                        "agent_id": str,
                        "meta": {},
                        "children": [...]
                    }
                    # 更多子节点...
                ]
            }

        Raises:
            requests.exceptions.RequestException: HTTP请求异常
            ValueError: API响应格式错误或请求失败
        """
        # 调用AgentClient的get_agent_subtree方法获取静态树
        return self.agent_client.get_agent_subtree(agent_id)

    async def get_dynamic_agent_tree(self, agent_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的动态Agent子树（静态树+运行时状态）

        Args:
            agent_id: 根节点Agent ID

        Returns:
            动态子树结构，格式如下：
            {
                "agent_id": str,              # 节点Agent ID
                "meta": {                     # 节点元数据
                    "name": str,              # Agent名称
                    "type": str,              # Agent类型
                    "is_leaf": bool,          # 是否为叶子节点
                    "weight": float,          # 权重值
                    "description": str        # 描述信息
                    # 其他元数据字段...
                },
                "runtime_state": {           # 运行时状态
                    "is_alive": bool,         # 是否存活
                    "status_label": str,      # 状态标签
                    "last_seen_seconds_ago": int,  # 最后活跃时间
                    "current_task": dict      # 当前任务信息
                },
                "children": [                 # 子节点列表（递归结构）
                    {
                        "agent_id": str,
                        "meta": {},
                        "runtime_state": {},
                        "children": [...]
                    }
                    # 更多子节点...
                ]
            }

        Raises:
            requests.exceptions.RequestException: HTTP请求异常
            ValueError: API响应格式错误或请求失败
        """
        # 1. 获取静态树
        static_tree = await self.get_static_agent_tree(agent_id)
        # 2. 注入运行时状态，返回动态树
        return await self.enrich_subtree_with_status(static_tree)
