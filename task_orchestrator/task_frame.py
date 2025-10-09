from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import time






class TaskFrame:
    def __init__(
        self,
        frame_id: str,
        task_id: str,
        caller_agent_id: str,
        target_agent_id: str,
        context: dict,
        parent_frame_id: Optional[str],
        tenant_id:str,
        capability: str =None      # 要执行的能力,
    ):
        self.frame_id = frame_id
        self.task_id = task_id
        self.tenant_id = tenant_id
        self.caller_agent_id = caller_agent_id
        self.target_agent_id = target_agent_id
        self.capability = capability
        self.context = context
        self.parent_frame_id = parent_frame_id
        self.sub_frames: List[str] = []  # child frame_ids
        self.status = "pending"  # pending, running, completed, failed
        self.result: Any = None
        self.error: Optional[str] = None
        self.created_at = time.time()

