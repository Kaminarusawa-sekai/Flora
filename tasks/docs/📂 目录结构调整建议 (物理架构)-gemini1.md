这是一个非常清晰且具备深度的流程设计。你现在的设计已经从“堆砌功能”转向了“工业级链路”。

为了让这个流程真正跑通，我们需要解决核心的**数据流转**（Data Flow）和**模块解耦**问题。特别是 `AgentActor`（决策大脑）与 `TaskExecutionService`（执行手脚）以及 `Capabilities`（工具箱）之间的交互。

以下是基于你提供的 12 步流程的**深度重构方案**。

------



### 📂 目录结构调整建议 (物理架构)



为了配合你的逻辑流，建议将文件结构微调，使其职责更明确：

- **`core/`** (新) -> 放原 `common` 中的业务逻辑
  - `interaction/` (Draft, Intent, ConversationManager)
- **`agents/`**
  - `orchestration/` (AgentActor, TaskCoordinator, TaskPlanner)
  - `execution/` (TaskExecutionService, ExecutionManager, Aggregators) **<-- 执行核心移到这里**
- **`capabilities/`** (纯工具，被动调用)
  - `tools/` (Data, Dify, Search)
  - `routing/` (TaskRouter, ContextResolver)
- **`scheduler/`** (LoopScheduler)

------



### 🔄 全链路详细交互设计 (Step-by-Step)



我们将这 12 步分为四个阶段：**交互解析阶段**、**规划调度阶段**、**执行分发阶段**、**结果反馈阶段**。



#### 第一阶段：交互解析 (Interaction Phase)



**Step ① & ②: 草稿与意图**

- **执行者**: `AgentActor` 调用 `Core.InteractionManager` (组合了 Draft + Intent)
- **输入**: `UserRequest(text, user_id, conversation_id)`
- **交互逻辑**:
  1. `AgentActor` 收到消息。
  2. 调用 `InteractionManager.process(text, history)`。
  3. **DraftCheck**: 检查 Redis 中的 `draft_key`。
     - *If Yes*: 返回 `DraftContext(previous_task_id, missing_params)`。
  4. **Intent**: 若无草稿，调用 `QwenAdapter`。
- **输出**: `IntentResult(type: [NEW_TASK | CHAT | MODIFY], params: {...})`

**Step ③ & ④: 任务操作与循环判断**

- **执行者**: `AgentActor`
- **逻辑**:
  - 如果 `IntentResult` 是修改/评论 -> 直接调用 `TaskRegistry.update()`。
  - 如果 `IntentResult` 是新任务 -> 调用 `_llm_decide_task_strategy`。
  - **Loop Check**: 如果 LLM 判定为循环任务：
    - 发送消息 `RegisterLoopTask` 给 `LoopSchedulerActor`。
    - `LoopSchedulerActor` 设置 RabbitMQ 定时器。
    - *End Flow* (等待触发)。
    - **触发时**: RabbitMQ -> `LoopScheduler` -> 发送 `ExecuteLoopTask` 给 `AgentActor` -> **跳转到 Step ⑤**。

------



#### 第二阶段：规划调度 (Planning Phase)



**Step ⑤: 能力路由 (Routing)**

- **执行者**: `AgentActor` 调用 `Capabilities.TaskRouter`
- **输入**: `TaskDescription`, `MemoryContext`
- **交互**:
  - `TaskRouter` 分析任务语义。
  - **分叉点**:
    - **Case A (子Agent)**: 这是一个大任务（如“写一份行业报告”），需要分派给 `ResearchAgent`。 -> 返回 `RouteResult(target="agent:research_01", type="AGENT")`。
    - **Case B (叶子能力)**: 这是一个具体动作（如“查询数据库”）。 -> 返回 `RouteResult(target="capability:mysql_tool", type="LEAF")`。
- **输出**: `RouteResult`

**Step ⑥: 任务规划 (Planning)**

- **执行者**: `AgentActor` 调用 `Capabilities.TaskPlanner`
- **逻辑**:
  - 如果 Step ⑤ 是 `LEAF`，跳过此步，直接封装为一个 `SingleTask`。
  - 如果 Step ⑤ 是 `AGENT` 且任务复杂，调用 `TaskPlanner.plan()` 生成 DAG (有向无环图)。
  - **SCC处理**: 识别强耦合任务，标记为 `TaskGroup`。
- **输出**: `ExecutionPlan(tasks=[SubTask1, SubTask2], dependencies={...})`

**Step ⑦: 任务分发 (Coordination)**

- **执行者**: `AgentActor` -> `TaskCoordinator`
- **动作**:
  - `AgentActor` 将 `ExecutionPlan` 交给 `TaskCoordinator`。
  - `TaskCoordinator` 创建父任务记录 (Status: RUNNING)。
  - 根据依赖关系，提取当前可执行的**任务批次**。
- **数据传输**: 发送消息 `ExecuteBatchRequest` 给 `TaskExecutionService`。

------



#### 第三阶段：执行分发 (Execution Phase)



**Step ⑧: 组任务管理 (Group Aggregation)**

- **类**: `TaskExecutionService` (接收者) -> `TaskGroupAggregator`
- **逻辑**:
  - `TaskExecutionService` 收到批次请求。
  - 实例化 `TaskGroupAggregator`。
  - **重试逻辑**: 包装在 `Tenacity` 或内部计数器中。

**Step ⑨: 并行执行判断与优化**

- **类**: `ExecutionManager`
- **逻辑**:
  - 检查 `TaskConfig`。
  - **Optuna 路径**: 如果 `strategy="OPTUNA"`, 调用 `OptunaOptimizer` 生成参数组合，生成多个并行的 Trial 任务。
  - **普通路径**: 直接并行分发。

**Step ⑩: 单任务执行 (递归/叶子判断)**

这是最关键的一步，决定了是递归调用还是真正干活。

- **类**: `TaskExecutionService`
- **输入**: `SubTaskContext`
- **逻辑**:
  - **检查 RouteResult (来自 Step ⑤)**:
  - **分支 A: 路由指向另一个 Agent (递归)**
    - 构建 `AgentTaskMessage`。
    - `self.send(target_agent_addr, AgentTaskMessage)`。
    - *等待异步结果*。
  - **分支 B: 路由指向具体 Capability (叶子节点)**
    - 进入 **Step ⑪ (具体执行)**。

------



#### 第四阶段：落地与反馈 (Landing Phase)



**Step ⑪: 具体执行与参数解析 (Leaf Execution)**

- **类**: `LeafExecutor` (新类，被 TaskExecutionService 调用)
- **逻辑**:
  1. **参数解析**: 调用 `ContextResolver.resolve(task_params, context_memory)`。
     - 例如：任务参数是 `userId=${prev_task.output.id}`，这里将其替换为真实 ID `12345`。
  2. **执行**:
     - `func = CapabilityRegistry.get_function(tool_name)`
     - `result = func(**resolved_params)`
- **输出**: `TaskResult(data=..., status=SUCCESS)`

**Step ⑪ (后半): 结果聚合**

- **类**: `ResultAggregator`
- **逻辑**:
  - 收集 Step ⑩ (递归Agent返回) 或 Step ⑪ (工具返回) 的结果。
  - 应用策略 (MapReduce / Append / Vote)。

**Step ⑫: 事件与返回**

- **类**: `TaskExecutionService` -> `EventBus` -> `AgentActor`
- **逻辑**:
  1. `EventBus.publish(TaskCompletedEvent)` -> 更新数据库/UI。
  2. `TaskExecutionService` 发送 `BatchCompletionMessage` 给 `AgentActor`。
  3. `AgentActor` 检查是否所有计划完成。
     - 未完成 -> `TaskCoordinator` 调度下一批 -> 回到 Step ⑦。
     - 已完成 -> 将最终结果返回给**最原始的调用方** (User or Parent Agent)。

------



### 🛠️ 核心类修改方案 (Specific Class Changes)





#### 1. `agents/agent_actor.py` (瘦身与决策)



Python

```
class AgentActor(Actor):
    def _handle_new_task(self, task_desc, sender):
        # 1. 交互与意图 (Step 1-2)
        # 这一步建议移到 RouterActor 分发前做，或者在这里快速做
        intent = self.interaction_manager.process(task_desc)
        
        # 2. 路由 (Step 5)
        # 区分是自己做(LEAF)还是找人做(AGENT)
        route_result = self.task_router.route(task_desc)
        
        if route_result.type == 'LEAF':
            # 自己就是干活的，直接转给 ExecutionService
            self.send(self.execution_service, ExecuteLeafRequest(task_desc))
        else:
            # 3. 规划 (Step 6)
            plan = self.planner.generate_plan(task_desc, route_result.target_agents)
            
            # 4. 启动协调器 (Step 7)
            # Coordinator 负责状态机管理
            self.coordinator.initialize(plan)
            self._dispatch_next_batch()

    def _dispatch_next_batch(self):
        # 获取下一批可执行任务
        batch = self.coordinator.get_next_batch()
        if batch:
            # 发送给执行服务 (Step 7 -> 8)
            self.send(self.execution_service, ExecuteBatchRequest(batch))
        else:
            # 全部完成 (Step 12)
            self._finalize_task()
```



#### 2. `agents/execution/task_execution_service.py` (通用执行器)



Python

```
class TaskExecutionService(Actor):
    def receiveMessage(self, msg, sender):
        if isinstance(msg, ExecuteBatchRequest):
            self._handle_batch(msg)
        elif isinstance(msg, ExecuteLeafRequest):
            self._handle_leaf(msg, sender)
    
    def _handle_batch(self, msg):
        # Step 8 & 9: 组管理与并行判断
        strategy = self.execution_manager.decide_strategy(msg.tasks)
        
        # 创建聚合器 Actor 来监控这批任务
        aggregator = self.createActor(TaskGroupAggregator)
        self.send(aggregator, InitializeGroup(msg.tasks, strategy))

    def _execute_single_task(self, task):
        # Step 10: 单任务分发
        if task.is_agent_call():
             # 递归：调用另一个 Agent
             self.send(task.target_agent_addr, AgentTaskMessage(task.payload))
        else:
             # 叶子节点执行
             self._execute_leaf_logic(task)

    def _execute_leaf_logic(self, task):
        # Step 11: 具体的脏活累活
        # 1. 解析参数 (Context Resolver)
        resolved_params = self.context_resolver.resolve(
            task.params, 
            task.context_memory
        )
        
        # 2. 查找能力函数
        capability_func = self.capability_registry.get(task.action)
        
        # 3. 执行并捕获结果
        try:
            result = capability_func(**resolved_params)
            self._report_success(task.id, result)
        except Exception as e:
            self._report_failure(task.id, e)
```



#### 3. `capabilities/routing/context_resolver.py` (参数解析器)



这是 Step 11 的关键。

Python

```
class ContextResolver:
    def resolve(self, params: dict, context: dict) -> dict:
        """
        将占位符参数转换为实际值
        Input: params={'user_id': '$context.last_result.id'}, context={'last_result': {'id': 123}}
        Output: {'user_id': 123}
        """
        resolved = {}
        for k, v in params.items():
            if isinstance(v, str) and v.startswith("$"):
                resolved[k] = self._extract_from_path(v, context)
            else:
                resolved[k] = v
        return resolved
```



### 💡 核心数据对象 (DTO)



为了保证模块间传输顺畅，必须定义标准消息：

1. **`TaskContext`**:
   - `memory`: 共享记忆（上游任务的输出）。
   - `trace_id`: 全链路追踪 ID。
   - `config`: 执行配置（超时、重试）。
2. **`ExecutionPlan`**:
   - `nodes`: 任务列表。
   - `edges`: 依赖关系。
3. **`AgentTaskMessage`**:
   - 用于 Agent 之间的递归调用。
   - 包含：`TaskDescription`, `ParentTaskId`.



### ⚡ 总结与改进点



1. **递归的统一**: 不管是调用子 Agent 还是调用 Python 函数，在 `TaskExecutionService` 看来都是一个 `Task`。如果是子 Agent，就发消息；如果是函数，就本地执行。
2. **上下文解析后置**: `ContextResolver` 放在**执行前一刻**（Step 11），确保能获取到最新的上游数据。
3. **循环任务外置**: `LoopScheduler` 作为一个外部触发器，不污染核心执行链路，只负责“按时推一把”。

这份设计将你的流程具体化到了类和方法的层面，清晰地界定了数据流向。你可以按照这个蓝图开始重构代码。