"""对话API模块，提供前端调用接口"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from interaction.capabilities.conversation.interface import IConversationManagerCapability
from interaction.task_orchestrator.interface import ITaskOrchestratorCapability
from interaction.common.models import Draft, TaskSpec, ClarificationRequest
from capabilities import get_capability

# 创建API路由
router = APIRouter(prefix="/api/v1/dialog", tags=["dialog"])

# 数据模型定义
class UserMessageRequest(BaseModel):
    """用户消息请求模型"""
    sessionId: str
    text: str
    userId: str = "default_user"

class DraftSubmitRequest(BaseModel):
    """草稿提交请求模型"""
    draftId: str
    userId: str = "default_user"

class DraftUpdateRequest(BaseModel):
    """草稿更新请求模型"""
    params: Dict[str, Any]
    userId: str = "default_user"

class TaskControlRequest(BaseModel):
    """任务控制请求模型"""
    userId: str = "default_user"

class TaskResumeRequest(BaseModel):
    """任务恢复请求模型"""
    input: Dict[str, Any]
    userId: str = "default_user"

# 内部服务
conversation_manager: Optional[IConversationManagerCapability] = None
task_orchestrator: Optional[ITaskOrchestratorCapability] = None


def initialize_api():
    """初始化API服务"""
    global conversation_manager, task_orchestrator
    
    # 获取对话管理器
    conversation_manager = get_capability(
        "conversation",
        expected_type=IConversationManagerCapability
    )
    
    # 获取任务协调器
    task_orchestrator = get_capability(
        "task_orchestrator",
        expected_type=ITaskOrchestratorCapability
    )
    
    if not conversation_manager:
        raise ValueError("Failed to initialize conversation manager")
    
    if not task_orchestrator:
        raise ValueError("Failed to initialize task orchestrator")
    
    # 初始化组件
    conversation_manager.initialize()
    task_orchestrator.initialize()


@router.post("/messages", response_model=Dict[str, Any])
async def send_user_message(request: UserMessageRequest):
    """
    发送用户消息
    
    前端调用此接口发送用户消息，后端处理后返回响应
    """
    try:
        # 使用对话管理器处理用户输入
        result = conversation_manager.handle_user_input(
            user_input=request.text,
            session_id=request.sessionId,
            user_id=request.userId
        )
        
        return {
            "messageId": f"msg_{hash(request.text)}",
            "responseText": result.get("message", ""),
            "draft": result.get("draft", None),
            "action": result.get("action", "chat")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理消息时发生错误: {str(e)}")


@router.get("/drafts/{sessionId}", response_model=List[Dict[str, Any]])
async def get_drafts(sessionId: str, userId: str = "default_user"):
    """
    获取会话的所有草稿
    
    Args:
        sessionId: 会话ID
        userId: 用户ID
    """
    try:
        drafts = conversation_manager.get_drafts_by_session(sessionId, userId)
        return [draft.to_dict() for draft in drafts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取草稿时发生错误: {str(e)}")


@router.get("/drafts/detail/{draftId}", response_model=Dict[str, Any])
async def get_draft_detail(draftId: str, userId: str = "default_user"):
    """
    获取草稿详情
    
    Args:
        draftId: 草稿ID
        userId: 用户ID
    """
    try:
        draft = conversation_manager.get_draft(draftId, userId)
        if not draft:
            raise HTTPException(status_code=404, detail="草稿不存在")
        return draft.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取草稿详情时发生错误: {str(e)}")


@router.post("/drafts/{draftId}/submit", response_model=Dict[str, Any])
async def submit_draft(draftId: str, request: DraftSubmitRequest):
    """
    提交草稿，创建任务
    
    Args:
        draftId: 草稿ID
    """
    try:
        result = conversation_manager.submit_draft(draftId, request.userId)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"提交草稿时发生错误: {str(e)}")


@router.patch("/drafts/{draftId}", response_model=Dict[str, Any])
async def update_draft(draftId: str, request: DraftUpdateRequest):
    """
    更新草稿
    
    Args:
        draftId: 草稿ID
    """
    try:
        draft = conversation_manager.update_draft(draftId, request.params, request.userId)
        return draft.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新草稿时发生错误: {str(e)}")


@router.delete("/drafts/{draftId}", response_model=Dict[str, Any])
async def delete_draft(draftId: str, userId: str = "default_user"):
    """
    删除草稿
    
    Args:
        draftId: 草稿ID
        userId: 用户ID
    """
    try:
        success = conversation_manager.delete_draft(draftId, userId)
        return {"success": success, "message": "草稿已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除草稿时发生错误: {str(e)}")


@router.get("/tasks/{sessionId}", response_model=List[Dict[str, Any]])
async def get_tasks(sessionId: str):
    """
    获取会话的所有任务
    
    Args:
        sessionId: 会话ID
    """
    try:
        tasks = task_orchestrator.get_tasks_by_session(sessionId)
        return [task.to_dict() for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务时发生错误: {str(e)}")


@router.get("/tasks/detail/{taskId}", response_model=Dict[str, Any])
async def get_task_detail(taskId: str):
    """
    获取任务详情
    
    Args:
        taskId: 任务ID
    """
    try:
        task = task_orchestrator.get_task(taskId)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务详情时发生错误: {str(e)}")


@router.post("/tasks/{taskId}/cancel", response_model=Dict[str, Any])
async def cancel_task(taskId: str, request: TaskControlRequest):
    """
    取消任务
    
    Args:
        taskId: 任务ID
    """
    try:
        result = task_orchestrator.cancel_task(taskId)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务时发生错误: {str(e)}")


@router.post("/tasks/{taskId}/pause", response_model=Dict[str, Any])
async def pause_task(taskId: str, request: TaskControlRequest):
    """
    暂停任务
    
    Args:
        taskId: 任务ID
    """
    try:
        result = task_orchestrator.pause_task(taskId)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停任务时发生错误: {str(e)}")


@router.post("/tasks/{taskId}/resume", response_model=Dict[str, Any])
async def resume_task(taskId: str, request: TaskResumeRequest):
    """
    恢复任务
    
    Args:
        taskId: 任务ID
    """
    try:
        result = task_orchestrator.resume_task(taskId, request.input)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复任务时发生错误: {str(e)}")


@router.post("/tasks/{taskId}/retry", response_model=Dict[str, Any])
async def retry_task(taskId: str, request: TaskControlRequest):
    """
    重试任务
    
    Args:
        taskId: 任务ID
    """
    try:
        result = task_orchestrator.retry_task(taskId)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重试任务时发生错误: {str(e)}")


@router.get("/tasks/{taskId}/logs", response_model=List[Dict[str, Any]])
async def get_task_logs(taskId: str):
    """
    获取任务日志
    
    Args:
        taskId: 任务ID
    """
    try:
        logs = task_orchestrator.get_task_logs(taskId)
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务日志时发生错误: {str(e)}")


# 内部接口（供任务协调器调用）
@router.post("/internal/request-input", response_model=Dict[str, Any])
async def request_input(request: Dict[str, Any]):
    """
    请求用户输入（由任务协调器调用）
    
    当任务执行需要额外输入时，任务协调器调用此接口
    """
    try:
        session_id = request.get("sessionId")
        task_id = request.get("taskId")
        field = request.get("field")
        prompt = request.get("prompt")
        input_type = request.get("inputType", "text")
        
        if not all([session_id, task_id, field, prompt]):
            raise ValueError("Missing required parameters")
        
        # 生成澄清请求
        clarification = conversation_manager.generate_clarification(
            task_id=task_id,
            missing_field=field,
            context={"session_id": session_id}
        )
        
        # 这里应该将澄清请求发送给前端，具体实现取决于通信方式（WebSocket或HTTP回调）
        
        return {
            "status": "success",
            "message": "澄清请求已生成"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成澄清请求时发生错误: {str(e)}")
