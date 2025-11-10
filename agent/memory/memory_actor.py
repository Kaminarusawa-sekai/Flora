# memory/memory_actor.py
from thespian.actors import Actor
# from .memory_interface import (
#     LoadMemoryForAgent,
#     IngestMemory,
#     BuildContextForLLM,
#     MemoryResponse,
#     MemoryError
# )
from agent.message import (
    LoadMemoryForAgent,
    IngestMemory,
    BuildContextForLLM,
    MemoryResponse,
    MemoryError
)
from llm_memory_system.manager import UnifiedMemoryManager
import logging

logger = logging.getLogger(__name__)

class MemoryActor(Actor):
    def __init__(self):
        self.manager: UnifiedMemoryManager = None
        self.user_id: str = None
        self.agent_id: str = None

    def receiveMessage(self, msg, sender):
        try:
            if isinstance(msg, LoadMemoryForAgent):
                self.user_id = msg.user_id
                self.agent_id = msg.agent_id
                self.manager = UnifiedMemoryManager(self.user_id)
                logger.info(f"MemoryActor({self.agent_id}) loaded for user {self.user_id}")
                self.send(sender, MemoryResponse("status", {
                    "user_id": self.user_id,
                    "agent_id": self.agent_id,
                    "loaded": True
                }))

            elif self.manager is None:
                err = "MemoryActor not initialized. Send LoadMemoryForAgent first."
                logger.error(err)
                self.send(sender, MemoryError(err))
                return

            elif isinstance(msg, IngestMemory):
                self.manager.ingest(msg.content, msg.role)
                self.send(sender, MemoryResponse("ingest", {"status": "success"}))

            elif isinstance(msg, BuildContextForLLM):
                context = self.manager.build_context_for_llm(msg.query)
                self.send(sender, MemoryResponse("context", context))

            else:
                logger.warning(f"Unknown message type: {type(msg)}")
                self.send(sender, MemoryError("Unsupported message type"))

        except Exception as e:
            logger.exception("MemoryActor error")
            self.send(sender, MemoryError(str(e)))