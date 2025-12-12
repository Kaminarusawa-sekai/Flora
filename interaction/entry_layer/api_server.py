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

from interaction.interaction_handler import DialogueOrchestrator, DialogueOrchestratorConfig
from interaction.common import UserInputDTO, SystemResponseDTO
from interaction.capabilities import (
    CommonUserInputManager,
    CommonIntentRecognitionManager,
    CommonDialogStateManager,
    CommonTaskDraftManager,
    CommonTaskQueryManager,
    CommonTaskControlManager,
    CommonScheduleManager,
    CommonTaskExecutionManager,
    CommonSystemResponseManager
)
from interaction.capabilities.base import MockTaskStorage

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
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'example_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    # 从capabilities字段中提取enabledManagers配置
    capabilities = config_data.get("capabilities", {})
    
    # 映射关系：能力名称 -> manager名称
    capability_to_manager = {
        "user_input": "userInput",
        "intent_recognition": "intentRecognition",
        "dialog_state": "dialogState",
        "task_draft": "taskDraft",
        "task_query": "taskQuery",
        "task_control": "taskControl",
        "schedule": "schedule",
        "task_execution": "taskExecution",
        "system_response": "systemResponse"
    }
    
    # 构建enabledManagers配置
    enabled_managers = {}
    for capability_name, manager_name in capability_to_manager.items():
        capability_config = capabilities.get(capability_name, {})
        enabled_managers[manager_name] = capability_config.get("enabled", False)
    
    orchestrator_config = DialogueOrchestratorConfig(
        enabled_managers=enabled_managers
    )
    
    # 创建任务存储
    task_storage = MockTaskStorage()
    
    # 初始化各个manager
    managers = {
        "userInput": CommonUserInputManager(),
        "intentRecognition": CommonIntentRecognitionManager(),
        "dialogState": CommonDialogStateManager(task_storage),
        "taskDraft": CommonTaskDraftManager(task_storage),
        "taskQuery": CommonTaskQueryManager(task_storage),
        "taskControl": CommonTaskControlManager(task_storage),
        "schedule": CommonScheduleManager(),
        "taskExecution": CommonTaskExecutionManager(task_storage),
        "systemResponse": CommonSystemResponseManager()
    }
    
    # 初始化各个manager
    for manager in managers.values():
        manager.initialize({})
    
    # 创建对话编排器
    _orchestrator = DialogueOrchestrator(orchestrator_config, managers)


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
        execution_manager = _orchestrator.managers.get("taskExecution")
        if not execution_manager:
            raise HTTPException(status_code=500, detail="任务执行管理器未初始化")
        
        # 恢复被中断的任务
        execution_manager.resume_interrupted_task(task_id, request.value)
        
        return ResumeTaskResponse(
            success=True,
            message="输入已提交，任务继续执行",
            task_id=task_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复任务失败: {str(e)}")


# 初始化对话编排器
init_orchestrator()
