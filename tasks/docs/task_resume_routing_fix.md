# 任务暂停-恢复路由修复说明

## 问题描述

当ExecutionActor发现缺少参数并暂停任务后，参数补充完成如何正确路由回原来的ExecutionActor继续执行？

**之前的问题**:
- ExecutionActor暂停后发送消息给AgentActor
- AgentActor没有保存ExecutionActor的地址
- 恢复时创建了新的ExecutionActor，而不是使用原来的
- 导致原ExecutionActor中保存的上下文丢失

## 解决方案

### 核心思路
在AgentActor中维护一个 `task_id -> execution_actor_address` 的映射，确保恢复时能找到原来的ExecutionActor。

### 修改内容

#### 1. ExecutionActor - 在暂停消息中包含自己的地址

**文件**: `capability_actors/execution_actor.py`

**修改**: `_request_missing_parameters` 方法

```python
def _request_missing_parameters(self, task_id: str, missing_params: List[str],
                               parameters: Dict[str, Any], reply_to: str) -> None:
    """请求补充缺失的参数"""
    # ... 其他代码 ...

    # 发送暂停消息，包含ExecutionActor自己的地址
    pause_response = {
        "message_type": "task_paused",
        "task_id": task_id,
        "missing_params": missing_params,
        "question": question,
        "execution_actor_address": self.myAddress  # ✅ 关键：添加自己的地址
    }

    self.send(reply_to, pause_response)
```

**关键点**: 使用 `self.myAddress` 获取当前ExecutionActor的地址并包含在消息中。

#### 2. AgentActor - 保存ExecutionActor地址映射

**文件**: `agents/agent_actor.py`

**修改1**: 在 `__init__` 中添加映射字典

```python
def __init__(self):
    # ... 其他初始化 ...
    self.task_id_to_sender: Dict[str, ActorAddress] = {}
    # ✅ 新增：保存task_id到ExecutionActor地址的映射
    self.task_id_to_execution_actor: Dict[str, ActorAddress] = {}
```

**修改2**: 在 `_handle_task_paused_from_execution` 中保存映射

```python
def _handle_task_paused_from_execution(self, message: Dict[str, Any], sender: ActorAddress):
    """处理来自ExecutionActor的task_paused消息"""
    task_id = message.get("task_id")
    execution_actor_address = message.get("execution_actor_address")

    # ✅ 关键：保存ExecutionActor地址到映射
    if execution_actor_address:
        self.task_id_to_execution_actor[task_id] = execution_actor_address
        self.log.info(f"Saved ExecutionActor address for task {task_id}")

    # 转发暂停消息给前台
    reply_to = self.task_id_to_sender.get(task_id)
    if reply_to:
        frontend_message = {
            "message_type": "task_paused",
            "task_id": task_id,
            "missing_params": missing_params,
            "question": question
        }
        self.send(reply_to, frontend_message)
```

**修改3**: 在 `_resume_paused_task` 中使用保存的地址

```python
def _resume_paused_task(self, task_id: str, parameters: Dict[str, Any], sender: ActorAddress):
    """恢复暂停的任务链"""
    self.log.info(f"Resuming paused task {task_id}")

    # ✅ 关键：从映射中获取原来的ExecutionActor地址
    exec_actor = self.task_id_to_execution_actor.get(task_id)

    if not exec_actor:
        self.log.error(f"Cannot find ExecutionActor for task {task_id}")
        self.send(sender, {
            "message_type": "task_error",
            "task_id": task_id,
            "error": "Cannot find the ExecutionActor for this task"
        })
        return

    # 发送恢复消息到原来的ExecutionActor
    exec_request = {
        "type": "resume_execution",
        "task_id": task_id,
        "parameters": parameters,
        "reply_to": self.myAddress
    }

    self.log.info(f"Sending resume request to original ExecutionActor")
    self.send(exec_actor, exec_request)  # ✅ 使用原来的ExecutionActor
```

**修改4**: 在任务完成时清理映射

```python
def _handle_execution_result(self, result_msg: Dict[str, Any], sender: ActorAddress):
    """处理执行结果"""
    task_id = result_msg.get("task_id")

    # ... 处理结果 ...

    # 清理映射
    if task_id in self.task_id_to_sender:
        del self.task_id_to_sender[task_id]
    # ✅ 清理ExecutionActor地址映射
    if task_id in self.task_id_to_execution_actor:
        del self.task_id_to_execution_actor[task_id]
```

## 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    任务暂停-恢复流程                          │
└─────────────────────────────────────────────────────────────┘

1. 任务执行阶段
   ↓
   ExecutionActor 发现缺少参数
   ↓
   ExecutionActor._request_missing_parameters()
   ├─ 调用 ConversationManager.pause_task_for_parameters()
   └─ 发送消息给 AgentActor:
      {
         "message_type": "task_paused",
         "task_id": "task_123",
         "missing_params": ["api_key"],
         "question": "请提供api_key",
         "execution_actor_address": <ExecutionActor地址>  ✅
      }
   ↓
2. 暂停消息转发
   ↓
   AgentActor._handle_task_paused_from_execution()
   ├─ 保存映射: task_id_to_execution_actor["task_123"] = <地址>  ✅
   └─ 转发给 InteractionActor:
      {
         "message_type": "task_paused",
         "task_id": "task_123",
         "question": "请提供api_key"
      }
   ↓
   InteractionActor → 用户
   显示: "请提供api_key"
   ↓
3. 用户补充参数
   ↓
   用户输入: "sk-xxxxx"
   ↓
   InteractionActor.receiveMessage("user_input")
   ↓
   ConversationManager.handle_user_input()
   ├─ is_parameter_completion() → True
   ├─ complete_task_parameters() → 完成
   └─ 返回:
      {
         "action": "parameter_completion",
         "task_id": "task_123",
         "parameters": {"api_key": "sk-xxxxx"}
      }
   ↓
   InteractionActor → AgentActor:
   {
      "message_type": "resume_task",
      "task_id": "task_123",
      "parameters": {"api_key": "sk-xxxxx"}
   }
   ↓
4. 恢复任务执行
   ↓
   AgentActor._handle_resume_task()
   ↓
   AgentActor._resume_paused_task()
   ├─ 从映射获取: exec_actor = task_id_to_execution_actor["task_123"]  ✅
   └─ 发送给原ExecutionActor:
      {
         "type": "resume_execution",
         "task_id": "task_123",
         "parameters": {"api_key": "sk-xxxxx"}
      }
   ↓
   ExecutionActor._handle_resume_execution()
   ├─ 从 _pending_requests 恢复上下文  ✅
   ├─ 合并参数
   └─ 继续执行任务
   ↓
5. 任务完成
   ↓
   ExecutionActor → AgentActor:
   {
      "type": "subtask_result",
      "task_id": "task_123",
      "result": {...}
   }
   ↓
   AgentActor._handle_execution_result()
   ├─ 处理结果
   ├─ 清理: del task_id_to_sender["task_123"]
   └─ 清理: del task_id_to_execution_actor["task_123"]  ✅
   ↓
   AgentActor → InteractionActor:
   {
      "message_type": "task_completed",
      "result": {...}
   }
   ↓
   InteractionActor → 用户
   显示结果
```

## 关键改进

### ✅ 之前的问题
```python
# 之前：创建新的ExecutionActor，丢失了上下文
exec_actor = self.createActor(ExecutionActor)  # ❌ 新Actor
self.send(exec_actor, exec_request)
```

### ✅ 修复后
```python
# 现在：使用原来的ExecutionActor，保留了上下文
exec_actor = self.task_id_to_execution_actor.get(task_id)  # ✅ 原Actor
if exec_actor:
    self.send(exec_actor, exec_request)
```

## 优势

1. **上下文保留**: 原ExecutionActor中的 `_pending_requests` 保留了任务上下文
2. **正确路由**: 恢复消息能准确送达原ExecutionActor
3. **内存清理**: 任务完成后自动清理映射，防止内存泄漏
4. **错误处理**: 找不到ExecutionActor时有明确的错误提示

## 测试建议

### 测试场景1: 正常暂停-恢复流程
```python
# 1. 发送需要参数的任务
task_msg = {
    "message_type": "user_input",
    "user_id": "test_user",
    "content": "执行Dify工作流"
}

# 2. 验证收到参数请求
# 3. 补充参数
param_msg = {
    "message_type": "user_input",
    "user_id": "test_user",
    "content": "sk-xxxxx"
}

# 4. 验证任务成功完成
```

### 测试场景2: 映射清理
```python
# 执行任务完成后
assert task_id not in agent_actor.task_id_to_execution_actor
assert task_id not in agent_actor.task_id_to_sender
```

### 测试场景3: ExecutionActor找不到
```python
# 删除映射后尝试恢复
del agent_actor.task_id_to_execution_actor[task_id]
# 验证收到错误消息
```

## 注意事项

1. **ExecutionActor生命周期**: ExecutionActor必须在整个暂停-恢复周期内保持存活
2. **映射清理**: 确保在所有结束路径（成功、失败、取消）都清理映射
3. **并发安全**: 如果有多个任务同时暂停，映射不会冲突（task_id唯一）
4. **超时处理**: 建议添加超时机制，长时间未恢复的任务应该清理映射

## 总结

通过在ExecutionActor暂停消息中包含自己的地址，并在AgentActor中维护地址映射，成功解决了任务暂停-恢复的路由问题。这确保了：
- ✅ 参数补充后能找到原ExecutionActor
- ✅ 原ExecutionActor的上下文得以保留
- ✅ 任务能正确恢复并继续执行
- ✅ 内存得到正确清理
