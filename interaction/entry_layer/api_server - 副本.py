#!/usr/bin/env python3
"""API路由定义"""
import json
import os
import sys
import asyncio
from typing import Dict, Any, Optional, DefaultDict
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, status, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from interaction_handler import InteractionHandler
from common import UserInputDTO, SystemResponseDTO
from capabilities.capability_manager import CapabilityManager
from capabilities.capbility_config import CapabilityConfig
from capabilities.registry import capability_registry
from capabilities.memory.interface import IMemoryCapability
from external.rag import DifyDatasetClient

# 创建FastAPI应用
app = FastAPI(title="AI任务管理API")

# 初始化对话编排器
_orchestrator = None

# 会话级别的事件队列管理器（内存实现）
SESSION_QUEUES = defaultdict(asyncio.Queue)


class UserMessageRequest(BaseModel):
    """用户消息请求模型"""
    utterance: str = Field(..., description="用户输入文本")
    timestamp: int = Field(..., description="时间戳")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class ResumeTaskRequest(BaseModel):
    """恢复任务请求模型"""
    slot_name: str = Field(..., description="待填充的槽位名称")
    value: Any = Field(..., description="槽位值")


class ResumeTaskResponse(BaseModel):
    """恢复任务响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    task_id: str = Field(..., description="任务ID")


class CoreMemoryRequest(BaseModel):
    """核心记忆设置请求模型"""
    key: str = Field(..., description="核心记忆键")
    value: str = Field(..., description="核心记忆值")


def init_orchestrator():
    """初始化对话编排器"""
    global _orchestrator
    # 1. 初始化能力管理器
    config_path = os.path.join(os.path.dirname(__file__), '.', '..', 'interaction_config.json')
    capability_manager = CapabilityManager(config_path)
    
    # 2. 自动发现和注册所有能力
    capability_manager.auto_register_capabilities()
    
    # 3. 初始化所有配置的能力
    capability_manager.initialize_all_capabilities()
    
    # 4. 创建交互处理器（使用新的空参数构造函数）
    _orchestrator = InteractionHandler()
    
    # 5. 将能力管理器的注册表传递给编排器（如果需要）
    # 注意：在当前设计中，对话编排器已经直接使用全局的 capability_registry
    # 所以这一步可能不需要，但如果需要的话可以添加
    # _orchestrator.registry = capability_manager.get_registry()


# 认证依赖
def get_current_user(x_user_id: Optional[str] = Header(None)):
    """获取当前用户ID

    如果未提供 X-User-ID，默认返回 "1"（方便开发测试）
    生产环境应修改为抛出 401 错误
    """
    if not x_user_id:
        return "1"  # 开发模式默认用户ID
        # 生产环境取消注释下面这行，并删除上面的 return
        # raise HTTPException(status_code=401, detail="未提供X-User-ID")
    return x_user_id


# 记忆沉淀函数
def trigger_memory_extraction(session_id: str, user_id: str):
    """触发记忆沉淀

    在会话结束后，将对话内容沉淀为结构化记忆
    """
    try:
        print(f"[后台任务] 开始为用户 {user_id} 的会话 {session_id} 沉淀记忆...")

        # 1. 获取对话历史
        from capabilities.context_manager.interface import IContextManagerCapability
        context_manager = capability_registry.get_capability("context_manager", IContextManagerCapability)
        recent_turns = context_manager.get_recent_turns(limit=20, session_id=session_id)

        if not recent_turns:
            print(f"[后台任务] 会话 {session_id} 没有对话记录，跳过记忆沉淀")
            return

        # 2. 格式化对话内容
        conversation_text = ""
        for turn in reversed(recent_turns):  # 反转为正序
            role = getattr(turn, 'role', 'unknown')
            utterance = getattr(turn, 'utterance', '')
            if role == 'user':
                conversation_text += f"用户: {utterance}\n"
            else:
                conversation_text += f"助手: {utterance}\n"

        # 3. 调用记忆能力存储
        from capabilities.memory.interface import IMemoryCapability
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)

        # 将整个对话作为记忆存储（Mem0 会自动提取关键信息）
        memory_cap.add_memory(user_id=user_id, text=conversation_text)

        print(f"[后台任务] 会话 {session_id} 的记忆沉淀完成")
    except ValueError as e:
        print(f"[后台任务] 记忆沉淀跳过（能力未启用）: {e}")
    except Exception as e:
        print(f"[后台任务] 记忆沉淀失败: {e}")


def _get_dify_dataset_client() -> DifyDatasetClient:
    api_key = os.getenv("DIFY_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="DIFY_API_KEY 未配置")
    base_url = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")
    return DifyDatasetClient(api_key=api_key, base_url=base_url)


def _get_dataset_id(dataset_id: Optional[str]) -> str:
    resolved = dataset_id or os.getenv("DIFY_DATASET_ID")
    if not resolved:
        raise HTTPException(status_code=400, detail="dataset_id 未提供且未配置 DIFY_DATASET_ID")
    return resolved


# 事件处理 & 推送函数
async def process_and_push_events(user_input: UserInputDTO, session_id: str, user_id: str, background_tasks: BackgroundTasks):
    """处理用户输入，并将每个事件推入会话队列"""
    try:
        # 调用编排器的流式方法
        async for event_type, data in _orchestrator.stream_handle_user_input(user_input):
            # 构造 SSE 格式的消息
            sse_event = {
                "event": event_type,
                "data": json.dumps(data, ensure_ascii=False)
            }
            # 推入队列
            await SESSION_QUEUES[session_id].put(sse_event)
        
        # 最后推送一个结束事件
        await SESSION_QUEUES[session_id].put({"event": "done", "data": "{}"})
        
        # 触发记忆沉淀
        background_tasks.add_task(trigger_memory_extraction, session_id, user_id)
    except Exception as e:
        # 推送错误事件
        error_data = {"error": str(e)}
        await SESSION_QUEUES[session_id].put({"event": "error", "data": json.dumps(error_data)})


@app.post("/conversations/{session_id}/messages", tags=["对话"], status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    session_id: str,
    request: UserMessageRequest,
    background_tasks: BackgroundTasks,
    x_user_id: str = Depends(get_current_user)
):
    """接收用户消息，并触发处理（事件将通过 /stream 推送）"""
    
    # 创建用户输入DTO
    user_input = UserInputDTO(
        session_id=session_id,
        user_id=x_user_id,
        utterance=request.utterance,
        timestamp=request.timestamp,
        metadata=request.metadata
    )
    
    # 异步处理消息（并将结果推送到该 session 的队列）
    background_tasks.add_task(process_and_push_events, user_input, session_id, x_user_id, background_tasks)
    
    return {"status": "accepted", "message": "Message received, processing..."}


@app.get("/conversations/{session_id}/stream", tags=["对话"])
async def stream_conversation_events(session_id: str):
    """标准 SSE 流：客户端通过 GET 订阅此端点"""

    async def event_generator():
        # 获取或创建该会话的事件队列
        queue = SESSION_QUEUES[session_id]
        try:
            while True:
                # 从队列中获取事件（阻塞等待）
                event = await queue.get()

                # 格式化为 SSE 协议
                event_type = event.get("event", "")
                if event_type:
                    yield f"event: {event_type}\n"
                yield f"data: {event['data']}\n\n"

                # 标记任务完成
                queue.task_done()

                # 收到 done 或 error 事件后结束流
                if event_type in ("done", "error"):
                    break

        except asyncio.CancelledError:
            # 客户端断开连接
            print(f"Client disconnected from session {session_id}")
            raise
        except Exception as e:
            # 其他错误
            yield f"event: error\n"
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/tasks/{task_id}/resume-with-input", response_model=ResumeTaskResponse, tags=["任务"])
async def resume_task(
    task_id: str,
    request: ResumeTaskRequest,
    x_user_id: str = Depends(get_current_user)
):
    """中断恢复接口（用于验证码等场景）
    
    当系统因中断等待用户输入时，前端需将用户输入定向提交给特定任务
    """
    try:
        # 调用任务执行管理器恢复中断的任务
        from capabilities.registry import capability_registry
        from capabilities.task_execution_manager import ITaskExecutionManagerCapability
        execution_manager = capability_registry.get_capability("taskExecution", ITaskExecutionManagerCapability)
        
        # 恢复被中断的任务
        execution_manager.resume_interrupted_task(task_id, request.value)
        
        return ResumeTaskResponse(
            success=True,
            message="输入已提交，任务继续执行",
            task_id=task_id
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"任务执行能力未找到: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")


@app.get("/memory/{user_id}/core", tags=["记忆"])
async def list_core_memory(user_id: str, limit: int = 50):
    """获取用户核心记忆列表"""
    try:
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
        return memory_cap.list_core_memories(user_id=user_id, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取核心记忆失败: {str(e)}")


@app.post("/memory/{user_id}/core", tags=["记忆"])
async def set_core_memory(user_id: str, request: CoreMemoryRequest):
    """设置或更新用户核心记忆"""
    try:
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
        memory_cap.set_core_memory(user_id=user_id, key=request.key, value=request.value)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置核心记忆失败: {str(e)}")


@app.delete("/memory/{user_id}/core/{key}", tags=["记忆"])
async def delete_core_memory(user_id: str, key: str):
    """删除用户核心记忆"""
    try:
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
        memory_cap.delete_core_memory(user_id=user_id, key=key)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除核心记忆失败: {str(e)}")


@app.get("/rag/documents", tags=["记忆"])
async def list_rag_documents(page: int = 1, limit: int = 20, dataset_id: Optional[str] = None, keyword: Optional[str] = None):
    """列出 Dify 数据集文档（文件库）"""
    client = _get_dify_dataset_client()
    resolved_dataset_id = _get_dataset_id(dataset_id)
    return client.list_documents(dataset_id=resolved_dataset_id, page=page, limit=limit, keyword=keyword)


@app.post("/rag/documents", tags=["记忆"])
async def upload_rag_document(
    file: UploadFile = File(...),
    dataset_id: Optional[str] = Form(None),
    indexing_technique: str = Form("high_quality"),
    process_mode: str = Form("automatic"),
):
    """上传文件到 Dify 数据集"""
    client = _get_dify_dataset_client()
    resolved_dataset_id = _get_dataset_id(dataset_id)
    return client.upload_document(
        dataset_id=resolved_dataset_id,
        file_obj=file.file,
        filename=file.filename,
        content_type=file.content_type,
        indexing_technique=indexing_technique,
        process_mode=process_mode,
    )


# 添加设计文档中指定的新接口

@app.get("/session/{session_id}", tags=["会话管理"])
async def get_session_info(session_id: str):
    """查询当前 Session 信息"""
    try:
        from capabilities.registry import capability_registry
        from capabilities.dialog_state_manager.interface import IDialogStateManagerCapability
        dialog_state_manager = capability_registry.get_capability("dialog_state", IDialogStateManagerCapability)
        # 从现有状态获取 user_id
        from external.database.dialog_state_repo import DialogStateRepository
        dialog_repo = DialogStateRepository()
        state = dialog_repo.get_dialog_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "session_id": state.session_id,
            "user_id": state.user_id,
            "created_at": state.last_updated.isoformat() if hasattr(state, 'last_updated') else None,
            "last_active": state.last_updated.isoformat() if hasattr(state, 'last_updated') else None,
            "current_intent": state.current_intent,
            "waiting_for_confirmation": state.waiting_for_confirmation,
            "name": state.name,
            "description": state.description,
            "request_id": state.current_request_id if hasattr(state, 'current_request_id') else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")


@app.get("/user/{user_id}/sessions", tags=["会话管理"])
async def get_user_sessions(user_id: str):
    """查询用户所有活跃 Sessions"""
    try:
        from external.database.dialog_state_repo import DialogStateRepository
        dialog_repo = DialogStateRepository()
        sessions = dialog_repo.get_sessions_by_user(user_id)
        return [
            {
                "session_id": state.session_id,
                "user_id": state.user_id,
                "created_at": state.last_updated.isoformat() if hasattr(state, "last_updated") else None,
                "last_active": state.last_updated.isoformat() if hasattr(state, "last_updated") else None,
                "current_intent": state.current_intent,
                "waiting_for_confirmation": state.waiting_for_confirmation,
                "name": state.name,
                "description": state.description,
                "request_id": state.current_request_id,
            }
            for state in sessions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user sessions: {str(e)}")


@app.post("/session/{session_id}/bind-user", tags=["会话管理"])
async def bind_user_to_session(session_id: str, user_id: str):
    """绑定用户到会话（匿名转正式）"""
    try:
        from capabilities.registry import capability_registry
        from capabilities.context_manager.interface import IContextManagerCapability
        context_manager = capability_registry.get_capability("context_manager", IContextManagerCapability)
        
        # 从现有状态获取旧的 user_id
        from external.database.dialog_state_repo import DialogStateRepository
        dialog_repo = DialogStateRepository()
        state = dialog_repo.get_dialog_state(session_id)
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        old_user_id = state.user_id
        
        # 更新会话中所有轮次的用户ID
        success = context_manager.update_turn_user_id(session_id, old_user_id, user_id)
        
        # 更新会话状态的 user_id
        state.user_id = user_id
        dialog_repo.save_dialog_state(state)
        
        return {
            "success": success,
            "message": "User bound to session successfully" if success else "Failed to bind user to session"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to bind user to session: {str(e)}")


@app.get("/session/{session_id}/history", tags=["对话历史"])
async def get_session_history(session_id: str, limit: int = 20, offset: int = 0):
    """查询会话对话历史"""
    try:
        from capabilities.registry import capability_registry
        from capabilities.context_manager.interface import IContextManagerCapability
        context_manager = capability_registry.get_capability("context_manager", IContextManagerCapability)
        turns = context_manager.get_turns_by_session(session_id, limit, offset)
        return [turn.model_dump() for turn in turns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session history: {str(e)}")


@app.get("/user/{user_id}/history", tags=["对话历史"])
async def get_user_history(user_id: str, limit: int = 20, offset: int = 0):
    """查询用户所有对话历史"""
    try:
        from capabilities.registry import capability_registry
        from capabilities.context_manager.interface import IContextManagerCapability
        context_manager = capability_registry.get_capability("context_manager", IContextManagerCapability)
        turns = context_manager.get_turns_by_user(user_id, limit, offset)
        return [turn.model_dump() for turn in turns]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user history: {str(e)}")


# 初始化对话编排器
init_orchestrator()
