# models.py
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ExecutionResult(BaseModel):
    task_id: str
    run_id: str
    timestamp: str
    status: str
    prompt: str
    output: Optional[str] = None
    metrics: Dict[str, Any]
    feedback: Optional[Dict[str, Any]] = None
    logs: Optional[List[str]] = None
    outputs: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class OptimizationAction(BaseModel):
    action_type: str
    params: Dict[str, Any]
    confidence: float
    reason: str
    valid_by_qwen: Optional[bool] = None
    qwen_suggestion: Optional[str] = None

class OptimizationEpisode(BaseModel):
    episode_id: str
    task_id: str
    state_before: Dict[str, Any]
    action_taken: OptimizationAction
    state_after: Optional[Dict[str, Any]] = None
    reward: Optional[float] = None
    applied_by: str  # auto / manual
    timestamp: str