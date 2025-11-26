# 整合草稿、意图和任务管理到AgentActor

## 1. 完善现有模块

<br />

1.0 设计传递的上下文，在上下文中增加类型和操作字段，例如类型是task，然后操作是add

### 1.1 修复draft中的问题

架构如下：User Input     │     ▼ \[全局意图识别] ←─┐     │            │     ├─ 新意图？───┤ → 中断当前流程，保存草稿（如有）     │            │     └─ 是“继续”？─┤ → 恢复最近草稿，回到追问状态                  │ \[状态机 FSM] ◄───┘   - idle   - collecting\_params (追问中)   - draft\_saved (草稿已存)

* 修复缺少的导入（TaskDraft、datetime、Generation、json、CONTINUE\_KEYWORDS）

* 修复函数定义（process\_user\_input\_complete应该是实例方法）

* 修复is\_continue\_request函数的缩进

* **草稿持久化**：将 `saved_drafts` 存入数据库（加 user\_id）

* **超时清理**：草稿超过 1 小时自动丢弃

* **多草稿支持**：用栈结构保存最近 3 个草稿

### 1.2 完善intent的问题

* 使用new\capabilities\llm\qwen\_adapter.py来调用大模型

* 修复缺少的导入

* 完善和draft的配合，在intent时可能也需要澄清

  <br />

### 1.3 完善tasks的问题

* 修复缺少的导入（datetime、Optional、Any、List、Dict、TaskType、TaskStatus）

* 修复重复的Task类定义（整合两个task类）

* 完善和draft的配合，在task时可能也需要澄清，如何保障不重复走

* **每个任务是一棵“历史树”**：初始创建为根节点，每次修改/执行/评论都生成新节点（不可变）。

* **支持多分支**（如“尝试不同方案”），但通常线性演进。

* **用户可通过自然语言引用任意历史状态**（如“用上周三那个版本重跑”）。

* **LLM 能基于上下文 + 元数据精准定位到正确的历史节点**。

* 历史任务相关代码在new\common\tasks\task\_node.py和new\common\tasks\task\_history\_graph.py

<br />

1.4 保障上面三个系统的架构统一，并且能够按user\_id区分

## 2. 整合到AgentActor

### 2.1 导入必要的模块

* 从common.draft导入ConversationManager, TaskDraft

* 从common.intent导入classify\_intent\_with\_qwen, should\_clarify

* 从common.tasks导入TaskRegistry, Task, TaskType

* 从capability\_actors.loop\_scheduler\_actor导入LoopSchedulerActor

### 2.2 扩展AgentActor类

* 添加conversation\_manager实例

* 添加task\_registry实例

* 添加clarification\_options状态

### 2.3 重写\_handle\_task方法

实现以下流程：

1. **草稿判断**：检查用户是否想继续草稿，或当前是否有未完成的草稿
2. **意图判断**：使用classify\_intent\_with\_qwen判断用户意图
3. **意图澄清**：如果意图模糊，生成澄清选项
4. **任务操作判断**：根据意图和用户输入，判断具体的任务操作
5. **任务执行**：根据任务操作执行相应的逻辑（现有\_handle\_task中的代码（包括节点路由和节点规划）
6. 循环任务执行是加入后就结束，然后等到时候发一个普通任务的消息来执行（可考虑加标识来防止重复添加）

### 2.4 实现任务操作处理

* 新增任务（new\_task）

* 修改任务（modify\_task）

* 评论任务（comment\_task）

* 重新执行任务（re\_run\_task）

* 取消任务（cancel\_task）

* 触发循环任务（trigger\_loop\_task）

* 修改循环间隔（modify\_loop\_interval）

* 暂停循环任务（pause\_loop\_task）

* 恢复循环任务（resume\_loop\_task）

### 2.5 整合循环任务管理

* 使用LoopSchedulerActor处理循环任务的注册和管理

* 实现add\_loop\_task方法

## 3. 实现智能判断

* 使用Qwen模型进行意图判断

* 使用Qwen模型进行任务操作判断

* 使用Qwen模型进行草稿判断

## 4. 测试和优化

* 确保所有流程正常工作

* 优化错误处理

* 确保日志记录完整

## 5. 预期效果

* AgentActor能够处理用户的各种意图

* 能够管理任务草稿

* 能够处理各种任务操作

* 能够智能判断用户意图和操作

* 能够管理循环任务

这个计划将确保AgentActor具备完整的任务管理能力，能够智能处理用户的各种请求。
