#!/usr/bin/env python3
"""API路由定义"""
import json
import os
import sys
import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, DefaultDict
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, status, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    """获取当前用户ID"""
    if not x_user_id:
        return "1"
        raise HTTPException(status_code=401, detail="未提供X-User-ID")
    return x_user_id


# 记忆沉淀函数
def trigger_memory_extraction(session_id: str, user_id: str):
    """触发记忆沉淀
    
    在会话结束后，将对话内容沉淀为结构化记忆
    """
    print(f"[后台任务] 开始为用户 {user_id} 的会话 {session_id} 沉淀记忆...")
    # 这里应该调用记忆管理模块的API来实现记忆沉淀
    # 例如：memory_manager.extract_and_store_memory(session_id, user_id)
    print(f"[后台任务] 会话 {session_id} 的记忆沉淀完成")


def _get_dify_dataset_client() -> DifyDatasetClient:
    """从配置中获取Dify数据集客户端"""
    # 从能力注册表获取memory能力，它包含了RAG配置
    from capabilities.registry import capability_registry
    from capabilities.memory.interface import IMemoryCapability
    
    memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
    
    # 获取RAG配置
    rag_config = memory_cap.rag_config if hasattr(memory_cap, 'rag_config') else {}
    
    api_key = rag_config.get("api_key")
    if not api_key:
        raise HTTPException(status_code=500, detail="DIFY_API_KEY 未配置")
    
    base_url = rag_config.get("base_url", "https://api.dify.ai/v1")
    return DifyDatasetClient(api_key=api_key, base_url=base_url)


def _get_dataset_id(dataset_id: Optional[str]) -> str:
    """从配置中获取数据集ID"""
    # 从能力注册表获取memory能力，它包含了RAG配置
    from capabilities.registry import capability_registry
    from capabilities.memory.interface import IMemoryCapability
    
    memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
    
    # 获取RAG配置
    rag_config = memory_cap.rag_config if hasattr(memory_cap, 'rag_config') else {}
    
    resolved = dataset_id or rag_config.get("dataset_id")
    if not resolved:
        raise HTTPException(status_code=400, detail="dataset_id 未提供且未配置")
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
        # 记录完整错误信息
        logger.exception(f"处理用户输入时发生错误，session_id={session_id}, user_id={user_id}")
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
                if "event" in event:
                    yield f"event: {event['event']}\n"
                yield f"data: {event['data']}\n\n"
                
                # 标记任务完成
                queue.task_done()
                
        except asyncio.CancelledError:
            # 客户端断开连接
            print(f"Client disconnected from session {session_id}")
            raise
        except Exception as e:
            # 其他错误
            logger.exception(f"SSE流处理错误，session_id={session_id}")
            yield f"event: error\n"
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            raise
    
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
        logger.exception(f"任务执行能力未找到，task_id={task_id}")
        raise HTTPException(status_code=500, detail=f"任务执行能力未找到: {str(e)}")
    except Exception as e:
        logger.exception(f"恢复任务失败，task_id={task_id}")
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")



@app.get("/memory/{user_id}/core", tags=["记忆"])
async def list_core_memory(user_id: str, limit: int = 50):
    """获取用户核心记忆列表
    
    Args:
        user_id: 用户唯一标识
        limit: 返回的记忆数量限制，默认50条
    
    Returns:
        list[dict]: 核心记忆列表，每条记忆包含以下字段：
            - id (str): 记忆唯一标识符
            - key (str): 记忆的键名
            - value (str): 记忆的内容值
    
    具体实现位于 mem0_memory.py 的 list_core_memories 方法中，
    从 mem0 客户端获取核心记忆数据并格式化返回。
    """
    try:
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
        return memory_cap.list_core_memories(user_id=user_id, limit=limit)
    except Exception as e:
        logger.exception(f"获取核心记忆失败，user_id={user_id}, limit={limit}")
        raise HTTPException(status_code=500, detail=f"获取核心记忆失败: {str(e)}")


@app.post("/memory/{user_id}/core", tags=["记忆"])
async def set_core_memory(user_id: str, request: CoreMemoryRequest):
    """设置或更新用户核心记忆"""
    try:
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
        memory_cap.set_core_memory(user_id=user_id, key=request.key, value=request.value)
        return {"success": True}
    except Exception as e:
        logger.exception(f"设置核心记忆失败，user_id={user_id}, key={request.key}")
        raise HTTPException(status_code=500, detail=f"设置核心记忆失败: {str(e)}")


@app.delete("/memory/{user_id}/core/{key}", tags=["记忆"])
async def delete_core_memory(user_id: str, key: str):
    """删除用户核心记忆"""
    try:
        memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
        memory_cap.delete_core_memory(user_id=user_id, key=key)
        return {"success": True}
    except Exception as e:
        logger.exception(f"删除核心记忆失败，user_id={user_id}, key={key}")
        raise HTTPException(status_code=500, detail=f"删除核心记忆失败: {str(e)}")


@app.get("/rag/documents", tags=["记忆"])
async def list_rag_documents(page: int = 1, limit: int = 20, dataset_id: Optional[str] = None, keyword: Optional[str] = None):
    """列出 Dify 数据集文档（文件库）"""
    try:
        client = _get_dify_dataset_client()
        resolved_dataset_id = _get_dataset_id(dataset_id)
        return client.list_documents(dataset_id=resolved_dataset_id, page=page, limit=limit, keyword=keyword)
    except Exception as e:
        logger.exception(f"列出 Dify 数据集文档失败，page={page}, limit={limit}, dataset_id={dataset_id}, keyword={keyword}")
        raise HTTPException(status_code=500, detail=f"列出 Dify 数据集文档失败: {str(e)}")


@app.post("/rag/documents", tags=["记忆"])
async def upload_rag_document(
    file: UploadFile = File(...),
    dataset_id: Optional[str] = Form(None),
    indexing_technique: str = Form("high_quality"),
    process_mode: str = Form("automatic"),
):
    """上传文件到 Dify 数据集"""
    try:
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
    except Exception as e:
        logger.exception(f"上传文件到 Dify 数据集失败，dataset_id={dataset_id}, filename={file.filename}, indexing_technique={indexing_technique}, process_mode={process_mode}")
        raise HTTPException(status_code=500, detail=f"上传文件到 Dify 数据集失败: {str(e)}")





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
        logger.exception(f"获取会话信息失败，session_id={session_id}")
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")


@app.get("/user/{user_id}/sessions", tags=["会话管理"])
async def get_user_sessions(user_id: str):
    """查询用户所有活跃 Sessions"""
    try:
        from external.database.dialog_state_repo import DialogStateRepository
        dialog_repo = DialogStateRepository()
        sessions = dialog_repo.get_sessions_by_user_id(user_id)
        
        # 构造返回结果，只返回必要的会话信息
        result = []
        for session in sessions:
            result.append({
                "session_id": session.session_id,
                "last_updated": session.last_updated,
                "user_id": session.user_id,
                "name": session.name,
                "description": session.description,
                "is_in_idle_mode": session.is_in_idle_mode
            })
        
        return result
    except Exception as e:
        logger.exception(f"获取用户会话列表失败，user_id={user_id}")
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
        logger.exception(f"绑定用户到会话失败，session_id={session_id}, user_id={user_id}")
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
        logger.exception(f"获取会话历史失败，session_id={session_id}, limit={limit}, offset={offset}")
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
        logger.exception(f"获取用户历史失败，user_id={user_id}, limit={limit}, offset={offset}")
        raise HTTPException(status_code=500, detail=f"Failed to get user history: {str(e)}")


@app.post("/conversations", tags=["会话管理"])
async def create_conversation(x_user_id: str = Depends(get_current_user)):
    """创建新对话
    
    创建一个新的对话会话，并返回会话ID和初始状态
    """
    try:
        import uuid
        # 生成唯一的会话ID
        session_id = str(uuid.uuid4())
        
        # 获取对话状态管理器
        from capabilities.registry import capability_registry
        from capabilities.dialog_state_manager.interface import IDialogStateManagerCapability
        dialog_state_manager = capability_registry.get_capability("dialog_state", IDialogStateManagerCapability)
        
        # 创建对话状态
        dialog_state = dialog_state_manager.get_or_create_dialog_state(session_id, x_user_id)
        
        return {
            "session_id": dialog_state.session_id,
            "user_id": dialog_state.user_id,
            "created_at": dialog_state.last_updated.isoformat(),
            "name": dialog_state.name,
            "description": dialog_state.description,
            "status": "created"
        }
    except Exception as e:
        logger.exception(f"创建对话失败，user_id={x_user_id}")
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


# 初始化对话编排器
init_orchestrator()
