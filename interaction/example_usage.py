#!/usr/bin/env python3
"""对话编排器使用示例"""
import json
from interaction_handler import DialogueOrchestrator, DialogueOrchestratorConfig
from common import UserInputDTO
from capabilities import (
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
from capabilities.base import MockTaskStorage


def main():
    """主函数"""
    # 1. 加载配置
    with open("example_config.json", "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    # 2. 从capabilities字段中提取enabledManagers配置
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
    
    # 提取全局配置和能力配置
    global_config = config_data.get("global_config", {})
    capabilities_config = capabilities
    
    # 2. 创建任务存储
    task_storage = MockTaskStorage()
    
    # 3. 初始化各个manager
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
    
    # 4. 初始化各个manager
    for manager in managers.values():
        manager.initialize({})
    
    # 5. 创建对话编排器
    orchestrator = DialogueOrchestrator(orchestrator_config, managers)
    
    # 6. 模拟用户输入
    user_input = UserInputDTO(
        session_id="test_session_001",
        user_id="user_001",
        utterance="创建一个任务，每天早上8点发送邮件",
        timestamp="2023-10-01T10:00:00",
        metadata={}
    )
    
    # 7. 处理用户输入
    response = orchestrator.handle_user_input(user_input)
    
    # 8. 打印响应
    print("\n系统响应：")
    print(f"响应文本：{response.response_text}")
    print(f"需要输入：{response.requires_input}")
    print(f"等待槽位：{response.awaiting_slot}")
    print(f"建议操作：{[action.title for action in response.suggested_actions]}")
    
    # 9. 关闭各个manager
    for manager in managers.values():
        manager.shutdown()


if __name__ == "__main__":
    main()
