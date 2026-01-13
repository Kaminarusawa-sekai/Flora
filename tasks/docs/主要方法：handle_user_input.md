#### 主要方法：`handle_user_input`

接收一个 `UserInputDTO`，返回一个 `SystemResponseDTO`。整个处理流程分为 6 个阶段：

------

##### **1. 用户输入管理**

- 检查 `userInput` Manager 是否启用。
- 调用 `managers["userInput"].process_input(input)` 处理原始输入，得到会话状态（`session_state`）。
- 若失败，返回兜底响应。

> ⚠️ 注意：这里获取的 `session_state` 后续似乎未被使用，可能是个遗留变量或待完善逻辑。

------

##### **2. 意图识别（Intent Recognition）**

- 如果启用了 `intentRecognition` Manager，则调用其 `recognize_intent` 方法。
- 若识别失败或未启用，则**默认 fallback 到 `IntentType.IDLE`（闲聊）**，置信度为 1.0。

------

##### **3. 对话状态管理**

- 必须存在 `dialogState` Manager，否则报错。
- 获取或创建当前会话的 `DialogStateDTO`。
- 将识别出的意图写入 `dialog_state.current_intent`。

------

##### **4. 意图路由与业务处理（核心逻辑）**

根据 `intent_result.intent` 的类型，分发到不同的业务 Manager：

| 意图类型                                                | 对应 Manager             | 功能                                 |
| ------------------------------------------------------- | ------------------------ | ------------------------------------ |
| `CREATE` / `MODIFY`                                     | `taskDraft`              | 更新任务草稿                         |
| `QUERY`                                                 | `taskQuery`              | 查询任务                             |
| `DELETE` / `CANCEL` / `PAUSE` / `RESUME_TASK` / `RETRY` | `taskControl`            | 控制任务生命周期                     |
| `SET_SCHEDULE`                                          | `schedule` + `taskDraft` | 设置定时任务（需两者都启用）         |
| `IDLE`                                                  | —                        | 固定回复：“好的，有需要随时告诉我！” |
| 其他                                                    | —                        | 提示用户换种说法                     |

- 每个分支都会检查对应 Manager 是否启用，未启用则返回功能未开启的兜底消息。
- 所有业务逻辑都包裹在 try-except 中，异常时返回错误信息。

结果存入 `result_data` 字典，包含响应文本、是否需要用户继续输入、槽位信息、展示数据等。

------

##### **5. 任务执行（可选）**

- 仅当满足以下条件时执行：
  - `taskExecution` Manager 启用；
  - `result_data` 中 `should_execute == True`；
  - 存在 `task_draft` 且其状态为 `"SUBMITTED"`。
- 调用 `taskExecution.execute_task(...)` 执行任务。
- 将执行上下文 ID 记录到 `dialog_state.active_task_execution`。
- 执行结果也存入 `result_data`。

------

##### **6. 生成系统响应**

- 如果启用了

   

  ```
  systemResponse
  ```

   

  Manager：

  - 调用其 `generate_response` 方法，传入会话 ID、响应文本、交互标志等。
  - **更新并持久化对话状态**（调用 `dialogState.update_dialog_state`）。
  - 返回生成的 `SystemResponseDTO`。

- 否则返回“响应生成器已关闭”的兜底消息。