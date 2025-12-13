#!/usr/bin/env python3
"""API路由定义"""
import json
import os
import sys
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from interaction.interaction_handler import InteractionHandler
from interaction.common import UserInputDTO, SystemResponseDTO
from interaction.capabilities.capability_manager import CapabilityManager
from interaction.capabilities.capbility_config import CapabilityConfig

# 创建FastAPI应用
app = FastAPI(title="AI任务管理API")

# 初始化对话编排器
_orchestrator = None


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


def init_orchestrator():
    """初始化对话编排器"""
    global _orchestrator
    
    # 1. 初始化能力管理器
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'example_config.json')
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
        raise HTTPException(status_code=401, detail="未提供X-User-ID")
    return x_user_id


@app.post("/conversations/{session_id}/messages", response_model=SystemResponseDTO, tags=["对话"])
async def send_message(
    session_id: str,
    request: UserMessageRequest,
    x_user_id: str = Depends(get_current_user)
):
    """主对话接口（核心入口）
    
    用户发送消息，系统返回响应（同步轮询模式）
    """
    try:
        # 创建用户输入DTO
        user_input = UserInputDTO(
            session_id=session_id,
            user_id=x_user_id,
            utterance=request.utterance,
            timestamp=request.timestamp,
            metadata=request.metadata
        )
        
        # 调用对话编排器处理用户输入
        response = _orchestrator.handle_user_input(user_input)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


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
        from interaction.capabilities.registry import capability_registry
        execution_manager = capability_registry.get_capability("taskExecution", object)
        
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


# 初始化对话编排器
init_orchestrator()
