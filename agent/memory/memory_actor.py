# memory/memory_actor.py
from thespian.actors import Actor
from .memory_interface import LoadMemoryForAgent, MemoryResponse, MemoryUpdate
import logging

logger = logging.getLogger(__name__)

def _load_memory_from_db(agent_id: str):
    """模拟从数据库加载记忆，实际可替换为 SQLAlchemy 等"""
    # 示例：返回 dict
    return {"user_pref": "dark_mode", "last_query": "flight to Tokyo"}

class MemoryActor(Actor):
    def __init__(self):
        self._memory = {}
        self._agent_id = None

    def receiveMessage(self, msg, sender):
        try:
            if isinstance(msg, LoadMemoryForAgent):
                self._agent_id = msg.agent_id
                self._memory = _load_memory_from_db(self._agent_id)
                logger.debug(f"Memory loaded for {self._agent_id}")
            elif isinstance(msg, MemoryResponse):  # 不应收到，防御性
                pass
            elif hasattr(msg, 'key') and hasattr(msg, 'value'):  # MemoryUpdate
                self._memory[msg.key] = msg.value
                self.send(sender, MemoryResponse(msg.key, "updated"))
            else:
                # 假设 msg 是 GetMemory(key)
                key = getattr(msg, 'key', None)
                if key is not None:
                    value = self._memory.get(key)
                    self.send(sender, MemoryResponse(key, value))
                else:
                    logger.warning(f"Unknown message to MemoryActor: {type(msg)}")
        except Exception as e:
            logger.exception(f"MemoryActor error: {e}")
            # 可选：向 sender 发送错误，但通常主 Actor 会超时处理