
#### 第一部分：核心架构调整




### 一、 核心架构问题诊断





#### 1. 调用链过长（"洋葱"太厚）



症状：一个任务的执行路径极其漫长。

例如：AgentActor -> TaskExecutionService -> ExecutionActor -> UniversalConnectorOrchestrator -> DifyConnector -> External API。

后果：

- **调试困难**：由于是 Actor 消息驱动，一旦中间断了，很难追踪是哪一层没回消息。
- **统合难点**：你需要在每一层都定义对应的 Message 类型（Request/Response），只要有一层的消息定义（Common/Messages）对不上，整个链条就崩了。



#### 2. Actor 与 Service/Class 的边界模糊



**症状**：

- `Agents` 文件夹里混杂了 `AgentActor`（真Actor）和 `TaskCoordinator`（看起来是纯逻辑类）。

- Capabilities Actor 里有 TaskExecutionService，这名字听起来像个单例服务，但它又持有一个 ExecutionActor。

  风险：Actor 是异步消息驱动的，而普通 Class/Service 通常是同步调用的。如果 AgentActor（异步）调用了 TaskCoordinator（同步），然后 TaskCoordinator 又试图去调用另一个 Actor（异步），这会造成死锁或者回调地狱。



#### 3. 功能模块的过度拆分（碎片化）



**症状**：

- **聚合器泛滥**：`ParallelTaskAggregatorActor`, `ResultAggregatorActor`, `TaskGroupAggregatorActor`。这三者功能高度相似，都是“发出去N个，收回N个，处理结果”。分开写会导致维护三套状态机逻辑。
- **记忆层级重复**：`AgentMemoryActor` -> `MemoryCapabilityActor` -> `UnifiedMemoryManager` -> `External Storage`。四层包装极其容易导致数据在传递中丢失参数。

------



### 二、 具体文件夹与模块的问题检查



以下是针对你提供的说明，逐个模块指出的具体问题和调整建议：



#### 1. Agents 文件夹（核心逻辑）



- **`TaskCoordinator` (coordination/task_coordinator.py)**
  - **问题**：它在 `Agents` 目录下，但看起来像是一个纯逻辑工具类。
  - **建议**：如果它不继承 Actor，只是辅助计算子任务，建议移入 `Common/Tasks` 或 `Capabilities/Decision`。不要让它停留在 `Agents` 文件夹产生误导。
- **`TreeManager` (tree/tree_manager.py)**
  - **问题**：它封装了 `AgentRegistry`，但 `AgentRegistry` 又在 `Agents` 根目录下。这里有循环依赖或层级倒置的风险。通常 Registry（注册表）是底层，Manager 是上层。
  - **建议**：将 `TreeManager` 视为 `External/AgentStructure` 的一部分，因为它主要处理 Neo4j/结构关系。`AgentActor` 应该只持有它的引用。
- **`AgentActor`**
  - **统合风险**：它的 `_handle_task` 逻辑太重了。它既要路由，又要规划，又要分发。
  - **建议**：`IntentRouter`（意图判断）应该前置。在消息到达 `AgentActor` 之前，或者在 `RouterActor` 阶段就应该大概知道意图，`AgentActor` 专注执行。



#### 2. Capabilities Actor 文件夹（最难统合的地方）



- **`TaskExecutionService` vs `ExecutionActor`**
  - **问题**：这是最冗余的部分。`TaskExecutionService` 负责调度 `ExecutionActor`，但 `ExecutionActor` 本身就是为了执行。
  - **修改建议**：**删除 `TaskExecutionService`**。让 `AgentActor` 直接给 `ExecutionActor` 发消息。如果需要逻辑判断（如工作流还是单任务），这属于 `AgentActor` 的规划职责，或者 `ExecutionActor` 内部的策略，不需要夹中间层。
- - 
- **`UniversalConnectorOrchestrator`**
  - **问题**：它和 `ExecutionActor` 职责冲突。`ExecutionActor` 应该能够直接调用 `Connector`。
  - **建议**：将其降级为 `External/ExecutionConnectors` 中的一个工具类（`ConnectorManager`），由 `ExecutionActor` 直接调用，而不是作为一个独立的 Actor。



#### 3. Capabilities 文件夹（纯逻辑）



- **位置合理性**：这部分设计得很好，作为纯 Python 类库存在。
- **风险**：`TaskRouter` 位于此处，但 `AgentActor` 也有路由逻辑。确保只有一处负责“决定谁来干活”。建议 `Capabilities/Routing` 负责决定谁来做， Actor调用相关逻辑。



#### 4. Common 文件夹



- **`ConversationManager` (Drafts)**
  - **致命问题**：`Draft`（草稿）状态存储在哪里？如果是存储在内存里（`TaskDraft` 仅仅是一个 Data Class），那么当系统重启或 Actor 迁移节点时，草稿就丢了。
  - **建议**：草稿应该持久化到 Redis 或 DB。`ConversationManager` 应该调用 `External/RedisAdapter`。
- **`Intent` 模块**
  - **问题**：意图识别通常需要调用 LLM (`Qwen`)。这意味着 `Common` 层依赖了 `Capabilities/LLM` 层。这违反了分层原则（Common 应该是最基础的，不依赖上层）。
  - **建议**：将 `Intent` 模块移到 `Capabilities/Decision` 或 `Agents/Utils` 中。



#### 5. Entry Layer & External



- **`EventActor` (External)**
  - **问题**：`External` 通常存放被调用的库（DB驱动、API Client）。`EventActor` 是一个活动的 Actor，放在 `External` 不合适。
  - **建议**：移入 `Agents/System` 或 `Capabilities Actor/System`。它是系统级 Actor。
- **`TenantRouter` (Entry Layer)**
  - **统合难点**：Entry Layer 是同步的 HTTP Server (FastAPI)，需要等待 Actor 的异步结果返回给前端。
  - **风险**：你通过 `RouterActor` 或 `EventActor` 拿结果时，需要使用 `Thespian` 的 `ask()` 模式（同步等待响应），这里容易超时。确保 `APIServer` 的超时设置足够长。

------



### 三、 具体的“统合”行动指南



因为你是分块写的，现在要拼起来，建议按照以下步骤重构，以减少复杂度：



#### 第一步：扁平化执行层（Critical）



不要让 `AgentActor` 像传话筒一样一层层传任务。

- **现状**：Agent -> Service -> ExecutionActor -> ConnectorOrchestrator -> Connector
- **目标**：Agent -> ExecutionActor -> Connector
- **操作**：
  1. 把 `TaskExecutionService` 的逻辑并入 `AgentActor` 或 `ExecutionActor`。
  2. 把 `UniversalConnectorOrchestrator` 改成非 Actor 的普通类，被 `ExecutionActor` 引用。



#### 第二步：统一内存访问



- **现状**：`AgentMemoryActor` 和 `MemoryCapabilityActor` 同时存在。
- **操作**：
  1. 全部删除，记忆部分已经移入agent_actor



#### 第三步：清理 Common 的依赖



- 检查 `common` 文件夹的 import。如果 `common` import 了 `capabilities` 或 `agents`，必须解耦。
- 例如 `Intent` 识别如果依赖大模型，通过依赖注入的方式传入 LLM Client，而不是直接 import。



#### 第四步：明确 Actor 寻址方式



在 `router_actor.py` 中，你使用 Redis 存储 Actor 引用。

- **检查点**：Thespian 框架生成的 ActorRef 能否直接序列化存入 Redis？通常 ActorRef 是 pickle 序列化的，但跨进程/跨机器反序列化需要特别注意配置。
- **建议**：在 Redis 中存储 Actor 的 `Address` (String)，取出后通过 `ActorSystem.createActor(..., globalName=...)` 或 `system.tell(address)` 重新建立联系。

------



#### 第二部分：流程架构调整


我设计的整个流程如下，用户输入 → routeractor分发至对应的agentactor ->  具体的 AgentActor    ↓  ① 草稿判断（TaskDraft + ConversationManager），判断用户输入是否是对之前的补充或者新开话题    ↓  ② 意图判断（IntentRouter + QwenAdapter），判断用户想进行什么操作，例如是执行任务，还是查数据，还是转发任务，就闲聊    ↓  ③ 任务操作判断（_llm_classify_task_operation），判断用户想对任务进行什么操作，是修改任务，还是重试任务，还是循环任务相关操作    ├─ 新任务 → ④    ├─ 评论/修改/重试 → 直接处理    └─ 循环任务操作 → LoopSchedulerActor    ↓  ④ 循环任务检测（_llm_decide_task_strategy）    ├─ 是循环任务 → LoopSchedulerActor → RabbitMQ → RabbitBridge → 定时触发    └─ 否 → ⑤    ↓  ⑤ 能力路由（TaskRouter 从capbilitiy获取）    ├─ 找到能力节点 （也是agent_actor）→ ⑥    └─ 未找到 → MCP Fallback    ↓  ⑥ 任务规划（TaskPlanner 从capbilitiy获取）    ├─ 生成子任务计划    └─ 支持SCC强耦合任务协同    ↓  ⑦ 任务分发（TaskCoordinator）需要事件通知    ├─ 创建子任务，传递子节点agent_actor的ref    └─ 发送到TaskExecutionService    ↓  ⑧ 组任务管理（TaskGroupAggregatorActor），需要事件通知    ├─ 批量执行    └─ 支持重试    ↓  ⑨ 并行执行判断（ExecutionManager）    ├─ 需要优化 → Optuna优化    └─ 普通执行 → ⑩    ↓  ⑩ 单任务执行（TaskExecutionService）    ├─ 由下一个agent_actor进行执行，继续上面这些操作，直至最后一层 ⑪ 具体执行（ResultAggregator from registry）     ├─ 判断自己是叶子节点，按照自己的说明调用excute_actor进行执行，过程中需要的参数通过capabilities\routing\context_resolver.py来获取     ↓  ⑪ 结果聚合（ResultAggregator from registry）     ↓  ⑫ 事件通知（EventBus）     └─ 发布任务完成/失败事件   ⑫ 返回（agent_actor）    └─ 将结果返回给调用方

我设计的流程实际上是一个**分形（Fractal）递归架构**：每个 `AgentActor` 既可以是管理者（Manager），也可以是执行者（Worker），取决于它在树状结构中的位置。

为了将你现有的“积木块”完美统合，我们需要明确**数据如何在这些块之间流转**，以及**谁持有谁的引用**。

以下是针对你 1-12 步流程的**具体修改方案**和**详细交互设计**。

------



### 一、 核心数据协议（Data Protocol）



在统合之前，必须统一“流通货币”。所有模块间交互必须遵循以下 Message 结构（修改 `common/messages`）：

1. **`AgentTaskMessage` (入参)**
   - `task_id`: 唯一任务ID
   - `content`: 用户原始输入或上级拆分的子任务描述
   - `context`: 字典，包含上下文（conversation_id, parent_task_output, shared_memory_ref）
   - `config`: 字典，包含策略控制（是否允许循环、重试次数、Optuna参数等）
2. **`TaskResult` (出参)**
   - `task_id`: 对应 ID
   - `status`: SUCCESS / FAILED / NEEDS_CLARIFICATION
   - `data`: 执行结果（JSON/Dict）
   - `meta`: 执行元数据（耗时、使用的工具、费用）

------



### 二、 详细统合方案（按流程步骤）





#### 阶段 1：入口与决策（流程 ① - ③）



涉及文件：agents/agent_actor.py

核心变动：移除 TaskExecutionService 在此阶段的介入，完全由 AgentActor 自身逻辑控制。

**修改 `AgentActor.receiveMessage` & `_handle_task`：**

Python

```
# agents/agent_actor.py

def _handle_task(self, msg, sender):
    user_input = msg.content
    user_id = msg.context.get('user_id')

    # --- 流程 ①：草稿判断 ---
    # 调用 common/draft/conversation_manager.py
    # 注意：不是 Actor 调用，而是直接类调用，因为草稿是轻量级逻辑
    draft_status = self.conversation_manager.process_user_input_complete(user_id, user_input)
    if draft_status == "DRAFT_SAVED":
        self.send(sender, TaskResult(status="PAUSED", data="草稿已保存"))
        return

    # --- 流程 ②：意图判断 ---
    # 调用 common/intent/intent_router.py
    intent = self.intent_router.classify_intent_with_qwen(user_input, self.memory_actor)
    
    if intent.type == "AMBIGUOUS":
         # 处理澄清逻辑...
         return

    # --- 流程 ③：任务操作判断 ---
    operation = self._llm_classify_task_operation(user_input, intent)
    
    if operation == "LOOP_TASK":
        # 转入流程 ④
        self._handle_loop_task_setup(msg, sender)
    elif operation == "NEW_TASK":
        # 转入流程 ⑤
        self._handle_new_task_execution(msg, sender)
```



#### 阶段 2：路由与分发（流程 ④ - ⑧）



**这是最复杂的“分叉点”。** 这里的关键是：`AgentActor` 需要判断自己是“分发者”还是“执行者”。

**修改 `AgentActor._handle_new_task_execution`：**

Python

```
# agents/agent_actor.py

def _handle_new_task_execution(self, msg, sender):
    # --- 流程 ④：循环检测 (略，逻辑同上) ---
    这里的关键：自己是不是叶子，通过treemanager相关代码解决
    如果我是叶子节点 -> 转流程 ⑩
    # --- 流程 ⑤：能力路由 ---
    #
    # 调用 capabilities/routing/task_router.py
    routing_result = self.task_router.select_best_actor(msg.content)
    
    
    # 如果 routing_result 指向子节点或需要拆分 -> 转流程 ⑥
    
    if self._is_leaf_node(routing_result):
        # --- 叶子节点路径 ---
        self._execute_leaf_logic(msg, sender)
    else:
        # --- 管理节点路径 (流程 ⑥ 任务规划) ---
        # 调用 capabilities/decision/task_planner.py
        subtasks = self.task_planner.generate_plan(msg.content)
        
        # --- 流程 ⑦ & ⑧：创建聚合器 Actor ---
        # 这里不要自己循环发送，而是创建一个临时的 Aggregator Actor 来管理这一组子任务
        # 这样 AgentActor 不会被阻塞，保持无状态
        
        aggregator_addr = self.createActor(TaskGroupAggregatorActor)
        
        # 构建 Group Request
        group_request = TaskGroupRequest(
            parent_task_id=msg.task_id,
            subtasks=subtasks, # 包含子任务描述
            strategy="optuna" if self._should_optimize() else "standard", # 流程 ⑨ 优化判断
            original_sender=sender # 让聚合器直接回给最初的请求者，或者回给 self
        )
        
        # 发送给聚合器，当前 Agent 任务暂时结束（等待回调）
        self.send(aggregator_addr, group_request)
```



#### 阶段 3：组任务聚合（流程 ⑧ - ⑨）



涉及文件：capabilities_actor/task_group_aggregator_actor.py

核心变动：集成 Optuna 逻辑，负责分发给下一层 AgentActor。

**修改 `TaskGroupAggregatorActor`：**

Python

```
# capabilities_actor/task_group_aggregator_actor.py

def receiveMessage(self, msg, sender):
    if isinstance(msg, TaskGroupRequest):
        self.pending_tasks = msg.subtasks
        self.results = {}
        self.parent_sender = msg.original_sender
        
        # --- 流程 ⑨：并行/优化执行判断 ---
        if msg.strategy == "optuna":
             # 调用 external/optimization/optuna_optimizer
             # 调整并发度或参数
             self._execute_with_optimization(msg.subtasks)
        else:
             self._execute_standard(msg.subtasks)

def _execute_standard(self, subtasks):
    for task in subtasks:
        # 关键点：这里是递归调用！
        # 聚合器把子任务发给 RouterActor，Router 找到对应的 子AgentActor
        # 从而实现：Agent -> Aggregator -> Child Agent -> ...
        
        # 获取子 Agent 地址 (通过 Routeractor 而非agent_registry，下面的代码要修改)
        target_agent = self.agent_registry.get_agent_actor(task.target_node_id)
        
        # 包装成 AgentTaskMessage
        sub_msg = AgentTaskMessage(
            task_id=task.id,
            content=task.description,
            context=self.parent_context
        )
        
        self.send(target_agent, sub_msg)
```



#### 阶段 4：叶子节点执行（流程 ⑩ - ⑪）



涉及文件：agents/agent_actor.py (叶子模式) 和 capabilities_actor/execution_actor.py

核心变动：这是递归的终点。这里需要真正执行工具或代码。

**修改 `AgentActor._execute_leaf_logic`：**

Python

```
# agents/agent_actor.py

def _execute_leaf_logic(self, msg, sender):
    # --- 流程 ⑩：准备单任务执行 ---
    # 不需要 TaskExecutionService，直接找 ExecutionActor
    
    # 获取 ExecutionActor (通常是单例或池化)
    exec_actor = self.createActor(ExecutionActor)
    
    # 构建执行请求
    exec_request = LeafTaskRequest(
        task_id=msg.task_id,
        content=msg.content,
        params=msg.context, # 此时参数可能还不完整
        sender=sender # 记录谁发起的
    )
    
    self.send(exec_actor, exec_request)
```

**修改 `capabilities_actor/execution_actor.py` (核心执行者)：**

Python

```
# capabilities_actor/execution_actor.py

def receiveMessage(self, msg, sender):
    if isinstance(msg, LeafTaskRequest):
        # --- 流程 ⑪-Part1：参数解析与上下文获取 ---
        # 调用 capabilities/routing/context_resolver.py
        # 这一步非常关键：将自然语言 + 历史记忆 -> 转化为函数参数
        
        resolved_params = self.context_resolver.resolve(
            input_text=msg.content,
            context=msg.params,
            memory_manager=self.memory_manager # 传入记忆管理器引用
        )
        
        if resolved_params.missing_info:
             # 如果缺参数，需要反向提问（此处省略复杂逻辑，假设成功）
             pass

        # --- 流程 ⑪-Part2：具体执行 ---
        try:
            # 1. 判断是普通函数还是连接器
            if self._is_connector_task(msg):
                # 直接调用 UniversalConnector (不再是 Actor，而是类实例)
                result = self.connector_orchestrator.execute(msg.content, resolved_params)
            else:
                # 执行本地 Capability 函数
                result = self.capability_registry.execute(msg.content, resolved_params)
            
            # --- 流程 ⑫：事件通知 ---
            # 发布成功事件
            self.event_bus.publish_task_event(msg.task_id, "COMPLETED", result)
            
            # 返回结果给调用者 (可能是 Aggregator，也可能是上级 Agent)
            self.send(sender, TaskResult(status="SUCCESS", data=result))
            
        except Exception as e:
            # 发布失败事件
            self.event_bus.publish_task_event(msg.task_id, "FAILED", str(e))
            self.send(sender, TaskResult(status="FAILED", error=str(e)))
```

------



### 三、 模块重构清单（To-Do List）



为了实现上述流程，你需要对现有代码进行以下**物理修改**：

1. **删除/降级模块**：
   - **Delete/Merge**: `task_execution_service.py` -> 逻辑并入 `AgentActor` (分发逻辑) 和 `ExecutionActor` (执行逻辑)。
   - **Downgrade**: `universal_connector_orchestrator.py` -> 改为普通 Class，不再继承 Actor。
2. **`agents/agent_actor.py`**：
   - 引入 `IntentRouter`, `ConversationManager`, `TaskPlanner` 作为类成员变量。
   - 实现 `_is_leaf_node()` 逻辑：查询 `AgentRegistry` 看自己是否还有子节点。
   - 实现**双模式切换**：如果是 Manager，生成子任务并发给 `TaskGroupAggregatorActor`；如果是 Worker，发给 `ExecutionActor`。
3. **`capabilities_actor/task_group_aggregator_actor.py`**：
   - 修改为递归发送者：它发送的消息目标是 `AgentActor`（下一层），而不是直接去执行。
   - 增加 `Optuna` 调用逻辑：在发送子任务前，优化子任务的参数或执行顺序。
4. **`capabilities_actor/execution_actor.py`**：
   - 这是真正的 Worker。
   - 引入 `ContextResolver` (from `capabilities/routing`)。
   - 在 `receiveMessage` 中，先调用 `ContextResolver.resolve()` 获取参数，再执行工具。
5. **`external/event_bus.py`**：
   - 确保 `AgentActor` 和 `ExecutionActor` 都能方便地 import 并调用单例的 `event_bus`。
6. agent_registry和treemanager合并，

------



### 四、 总结流程图（数据流向）



Code snippet

```
graph TD
    User[User Input] --> RouterActor
    RouterActor --> AgentActor_Root[AgentActor (Root)]
    
    subgraph "AgentActor Root Logic"
        AgentActor_Root --> Draft[① ConversationManager]
        AgentActor_Root --> Intent[② IntentRouter]
        AgentActor_Root --> Classify[③ Task Operation]
        AgentActor_Root --> Loop[④ Loop Check]
    end
    
    Classify -->|Loop| LoopScheduler
    Loop -->|No Loop| Router[⑤ TaskRouter]
    
    Router -->|Found Node| Planner[⑥ TaskPlanner]
    Planner -->|Subtasks| Aggregator[⑧ TaskGroupAggregatorActor]
    
    subgraph "Recursive Distribution"
        Aggregator -->|Msg: AgentTask| AgentActor_Child1[AgentActor (Child/Leaf)]
        Aggregator -->|Msg: AgentTask| AgentActor_Child2[AgentActor (Child/Leaf)]
    end
    
    subgraph "Leaf Execution (Step 10-11)"
        AgentActor_Child1 -->|Msg: LeafRequest| ExecActor[⑩ ExecutionActor]
        
        ExecActor -->|Resolve Params| ContextResolver[capabilities/context_resolver]
        ContextResolver -->|Query Memory| Memory[MemoryManager]
        
        ExecActor -->|Execute| Connector[UniversalConnector / Tool]
        
        Connector --> Result
    end
    
    Result -->|Msg: TaskResult| Aggregator
    Aggregator -->|Event| EventBus[⑫ EventBus]
    Aggregator -->|Final Result| AgentActor_Root
```



### 这里的关键修改点总结：



1. **AgentActor 是核心大脑**：它吞并了原有的 `TaskCoordinator` 和部分 `ExecutionService` 的职责。
2. **Aggregator 是中转站**：负责管理并发和重试，连接父 Agent 和子 Agent。
3. **ExecutionActor 是手脚**：负责参数填充（Consult Resolver）和最后的一击（Run Tool）。



#### 第三部分：agent与capbility_actor架构调整



针对你“**统合不起来**”的痛点，核心原因在于**中间层（Service层）和Actor层混用**，导致数据流断裂。

我们将聚焦于 **`Agents/agent_actor.py`** (大脑) 与 **`Capabilities Actor/execution_actor.py`** (手脚) 之间的直接交互。我们将废除 `TaskExecutionService` 的“中介”角色，让通信变得直接且透明。

以下是 **第一阶段：核心执行链路重构** 的详细方案。

------



### 第一步：统一数据传输协议 (Data Transport Object)



在两个 Actor 之间传输数据，必须有统一的“快递盒”。请在 `common/messages/task_messages.py` 中确认或定义以下两个核心消息类。这是所有交互的基础。



#### 1. `AgentTaskMessage` (发出的任务)

这边要针对各个actor



这是 `AgentActor` 发给 `ExecutionActor` 的指令。

Python

```
# common/messages/task_messages.py

@dataclass
class AgentTaskMessage:
    task_id: str              # 任务唯一ID
    task_type: str            # "LEAF_EXECUTION" (叶子执行) 或 "SUBTASK_GROUP" (子任务组)
    content: str              # 自然语言指令 或 结构化参数
    context: Dict[str, Any]   # 上下文：{ "memory_ref": "...", "user_id": "...", "parent_result": "..." }
    sender_addr: Any          # 发起者的 Actor 地址 (用于回调)
    
    # 新增：指定执行器类型，避免 ExecutionActor 再次猜测
    execution_mode: str = "standard"  # "standard"(本地能力), "connector"(外部连接器), "dify"(工作流)
```



#### 2. `TaskExecutionResult` (收回的结果)



这是 `ExecutionActor` 回传给 `AgentActor` 的报告。

Python

```
# common/messages/task_messages.py

@dataclass
class TaskExecutionResult:
    task_id: str
    status: str               # "SUCCESS", "FAILED", "NEED_MORE_INFO"
    result_data: Any          # 执行结果数据
    error_msg: Optional[str] = None
    usage: Optional[Dict] = None # Token消耗等元数据
```

------



### 第二步：改造 `Capabilities Actor` 端



我们要解决 **`UniversalConnectorOrchestrator`** 和 **`TaskExecutionService`** 造成的冗余。



#### 1. 降级 `UniversalConnectorOrchestrator`



现状：它是一个 Actor，导致 ExecutionActor 调用它时需要异步等待，增加了复杂性。

修改方案：将其改为普通 Python 类（单例或工具类），让 ExecutionActor 直接 import 并调用。

- **文件位置**：移动至 `capabilities/connectors/connector_manager.py` (建议新建或重命名)。
- **代码调整**：去掉 `Actor` 继承，保留 `execute` 方法。



#### 2. 重构 `execution_actor.py` (全能执行者)



这个类将成为 `AgentActor` 唯一需要对话的“包工头”。

**修改文件**：`capabilities_actor/execution_actor.py`

Python

```
from thespian.actors import Actor
from common.messages.task_messages import AgentTaskMessage, TaskExecutionResult
# 引入降级后的连接器管理器
from capabilities.connectors.connector_manager import UniversalConnectorManager 
# 引入本地能力注册表
from capabilities.registry import CapabilityRegistry 

class ExecutionActor(Actor):
    def __init__(self):
        super().__init__()
        self.connector_manager = UniversalConnectorManager()
        self.capability_registry = CapabilityRegistry()
        # 初始化 DataActor 等引用（如果需要查数据）
        
    def receiveMessage(self, msg, sender):
        if isinstance(msg, AgentTaskMessage):
            self._handle_execution(msg, sender)
    
    def _handle_execution(self, msg: AgentTaskMessage, sender):
        try:
            result_data = None
            
            # 分流逻辑：根据 mode 决定是用本地函数还是外部连接器
            if msg.execution_mode == "connector":
                # 直接同步调用，不再发消息给 Orchestrator Actor
                result_data = self.connector_manager.execute(
                    instruction=msg.content, 
                    params=msg.context
                )
            elif msg.execution_mode == "dify":
                # 这里可以选择调用 DifyActor，或者直接集成 DifyConnector
                # 为了简单，建议通过 connector_manager 统一管理 Dify
                result_data = self.connector_manager.execute_dify(msg.content, msg.context)
            else:
                # 本地能力执行 (Python 函数)
                # 解析参数 -> 执行
                func = self.capability_registry.get_function(msg.content) # 需配合 ContextResolver
                result_data = func(**msg.context.get('params', {}))

            # 执行成功，打包返回
            response = TaskExecutionResult(
                task_id=msg.task_id,
                status="SUCCESS",
                result_data=result_data
            )
            self.send(sender, response)

        except Exception as e:
            # 异常处理
            error_response = TaskExecutionResult(
                task_id=msg.task_id,
                status="FAILED",
                result_data=None,
                error_msg=str(e)
            )
            self.send(sender, error_response)
```

------



### 第三步：改造 `Agents` 端



我们要移除 **`TaskExecutionService`**，让 `AgentActor` 拿回控制权。

**修改文件**：`agents/agent_actor.py`

我们需要修改 `_handle_new_task` 逻辑，明确它是如何把任务扔给上面的 `ExecutionActor` 的。

Python

```
# agents/agent_actor.py

# 引入 ExecutionActor 类引用，用于创建
from capabilities_actor.execution_actor import ExecutionActor
from common.messages.task_messages import AgentTaskMessage, TaskExecutionResult

class AgentActor(Actor):
    # ... __init__ 等其他代码保持不变 ...

    def _handle_new_task(self, task_msg, sender, current_desc, parent_task_id):
        """
        对应你流程中的 ④ -> ⑤ -> ⑩
        """
        
        # 1. 路由决策 (Step ⑤)
        # 假设 TaskRouter 返回结果表明这是一个 "LEAF" (叶子) 任务，不需要再分拆
        # 如果是 "NODE" 任务，则走 TaskPlanner -> Aggregator 流程 (稍后讲)
        is_leaf_task = self.task_router.is_leaf_task(current_desc)

        if is_leaf_task:
            # 2. 准备执行 (Step ⑩)
            # 不再调用 TaskExecutionService，直接找 ExecutionActor
            
            # A. 确定执行模式 (是调 API 还是跑本地代码？)
            # 这可以通过简单的关键词匹配或 Router 返回的元数据决定
            exec_mode = "standard"
            if "dify" in current_desc.lower():
                exec_mode = "dify"
            elif "connect" in current_desc.lower():
                exec_mode = "connector"
            
            # B. 启动/获取执行 Actor
            # 注意：可以使用 createActor 创建临时的，也可以用全局单例
            # 建议：如果是短任务，创建临时的；如果是高频，持有引用
            executor = self.createActor(ExecutionActor)
            
            # C. 打包消息
            payload = AgentTaskMessage(
                task_id=task_msg.task_id,
                task_type="LEAF_EXECUTION",
                content=current_desc,
                context={
                    "user_id": self.user_id,
                    "memory_params": self.extracted_params # 之前步骤提取的参数
                },
                sender_addr=self.myAddress, # 告诉 executor 执行完回给我
                execution_mode=exec_mode
            )
            
            # D. 发送
            self.send(executor, payload)
            
            # E. 更新状态：等待执行结果
            self.state_manager.set_task_status(task_msg.task_id, "RUNNING")
            
        else:
            # 这是一个复杂任务，进入 Step ⑥ 任务规划
            self._handle_complex_task_planning(task_msg, sender)

    def receiveMessage(self, message, sender):
        # ... 处理其他消息 ...
        
        # F. 处理执行结果 (Step ⑪ 的回调)
        if isinstance(message, TaskExecutionResult):
            self._handle_execution_result(message, sender)

    def _handle_execution_result(self, result: TaskExecutionResult, sender):
        if result.status == "SUCCESS":
            # 1. 写入记忆
            self.memory_actor.store_result(result.task_id, result.result_data)
            
            # 2. 如果这是父任务的子任务，检查是否聚合完成
            if self.current_aggregator:
                 # 通知聚合器
                 self.send(self.current_aggregator, result)
            else:
                 # 3. 如果是根任务，直接返回给用户 (Step ⑫)
                 final_response = self._format_response(result.result_data)
                 # 假设 original_sender 在上下文中保存了
                 self.send(self.original_client_addr, final_response)
                 
                 # 4. 发布事件
                 self.event_bus.publish("TASK_COMPLETED", result.task_id)
                 
        elif result.status == "FAILED":
            # 触发 MCP Fallback 机制 (Step ⑤ 的 fallback)
            self._trigger_fallback(result.task_id, result.error_msg)
```

------



### 第四步：清理中间件



现在，`agents/agent_actor.py` 直接控制 `capabilities_actor/execution_actor.py`。

**请执行以下删除/归档操作**：

1. **删除 `agents/task_execution_service.py`**：它的调度逻辑已经移入了 `AgentActor._handle_new_task`。
2. **降级 `capabilities_actor/universal_connector_orchestrator.py`**：将类中的逻辑提取出来，变成 `capabilities/connectors` 下的一个普通类。`ExecutionActor` 不需要发消息给它，而是直接实例化调用。

------



### 总结我们刚刚完成的“连接”



通过这一轮修改，我们打通了 **Step ⑩ (单任务执行)** 的闭环：

1. **AgentActor** 接收到请求，判断为叶子任务。
2. **AgentActor** 直接创建 `AgentTaskMessage` (包含 `execution_mode`)。
3. **AgentActor** 直接发送给 `ExecutionActor`。
4. **ExecutionActor** 接收消息，根据 `mode` 直接调用本地 Python 函数或 Connector 类（不再异步跳跃）。
5. **ExecutionActor** 执行完毕，打包 `TaskExecutionResult` 发回给 `AgentActor`。
6. **AgentActor** 在 `receiveMessage` 中捕获结果，并决定是返回用户还是继续聚合。




#### 第四部分：capbility_actor与Capabilities架构调整

好的，我们进入下一层。这一层是系统的**实干层**。

**核心逻辑**：`Capabilities Actor` 文件夹中的 Actor 本质上是 **"异步工头"**，而 `Capabilities` 文件夹中的 Python 类才是真正干活的 **"工人"**。

如果不分清楚这一层，你的系统会出现“Actor 里写满业务逻辑”的臃肿情况，导致难以测试和复用。

以下是 **Capabilities Actor 层** 与 **Capabilities 层** 的具体交互设计方案。

------



### 一、 核心机制：注册表模式 (The Glue)



所有 Capability（能力）都必须通过 `Registry` 获取。Actor 不应该直接 `new` 一个工具类，而是问注册表要。

**交互模式**：

1. 系统启动时，`Capabilities/Registry.py` 加载所有插件。
2. Actor 启动时 (`__init__`)，获取 `CapabilityRegistry` 单例。
3. Actor 处理消息时，通过 Registry 获取具体的实例来执行函数调用。

------



### 二、 模块级详细交互设计



我们逐个击破你提到的核心模块。



#### 1. 任务执行：ExecutionActor $\leftrightarrow$ Connectors & Routing



这是最复杂的交互，涉及参数解析、连接器调用和结果执行。

- **Actor**: `capabilities_actor/execution_actor.py`
- **Capabilities**:
  - `capabilities/routing/context_resolver.py` (参数解析)
  - `capabilities/connectors/connector_manager.py` (通用连接器，原 Orchestrator 降级)
  - `capabilities/registry.py` (获取本地函数)

**交互代码示例**：

Python

```
# capabilities_actor/execution_actor.py

class ExecutionActor(Actor):
    def __init__(self):
        # 1. 初始化引用
        self.registry = CapabilityRegistry()
        self.connector_manager = UniversalConnectorManager() # 降级后的类
        # 实例化参数解析器 (来自 Capabilities 层)
        from capabilities.routing.context_resolver import ContextResolver
        self.context_resolver = ContextResolver()

    def _handle_execution(self, msg: AgentTaskMessage, sender):
        # --- 阶段 A: 参数解析 (交互 Capabilities/Routing) ---
        # Actor 将自然语言 + 上下文 交给 Resolver
        # Resolver 内部可能会调用 MemoryManager 查阅历史
        resolved_context = self.context_resolver.resolve(
            instruction=msg.content,
            context=msg.context
        )
        
        # 检查参数缺失
        if resolved_context.missing_params:
            self.send(sender, TaskExecutionResult(status="NEED_MORE_INFO", ...))
            return

        # --- 阶段 B: 执行 (交互 Capabilities/Connectors 或 Registry) ---
        try:
            result = None
            if msg.execution_mode == "connector":
                # 同步调用 Connector Manager
                # 数据流：Actor -> Manager -> SpecificConnector (e.g. Dify)
                result = self.connector_manager.execute(
                    connector_name=msg.target_tool, 
                    params=resolved_context.params
                )
            else:
                # 本地能力执行
                # 从注册表拿函数 -> 执行
                tool_func = self.registry.get_capability(msg.target_tool)
                result = tool_func(**resolved_context.params)

            self.send(sender, TaskExecutionResult(status="SUCCESS", result_data=result))
            
        except Exception as e:
            self.send(sender, TaskExecutionResult(status="FAILED", error_msg=str(e)))
```



#### 2. 数据访问：DataActor $\leftrightarrow$ DataAccess



`DataActor` 是数据的大门，防止多个 Agent 同时写入导致混乱，或者提供统一的查询接口。

- **Actor**: `capabilities_actor/data_actor.py`
- **Capabilities**: `capabilities/data_access/data_accessor.py`

**数据流转**：

1. **Request**: `DataQueryRequest(sql="SELECT...", type="mysql")`
2. **Actor**: `DataActor` 接收消息。
3. **Call**: 调用 `self.data_accessor.query(request.sql)`。
4. **Logic (Capabilities层)**:
   - `DataAccessor` 检查缓存。
   - 如果没缓存，根据 type 路由到 `MySQLDataSource`。
   - `MySQLDataSource` 执行 SQL。
5. **Return**: 返回 `pd.DataFrame` 或 `List[Dict]`。
6. **Actor**: 将结果包装为 `DataQueryResponse` 发回。

**关键修改**：确保 `DataActor` 不包含任何 SQL 拼接逻辑，全扔给 `DataAccessor`。



#### 3. 记忆管理：MemoryActor $\leftrightarrow$ LLM Memory



注意：你之前有两个 Memory Actor (`AgentMemoryActor` 和 `MemoryCapabilityActor`)。现在我们明确：`AgentMemoryActor` (在 Agents 层) 是大脑的一部分，它通过发送消息给 `MemoryCapabilityActor` (在 Capabilities Actor 层) 来进行繁重的读写，或者直接调用 Manager。

**推荐方案**：为了性能，`Agent` 层通常直接调用 `UnifiedMemoryManager`。但如果你想做异步存储（不阻塞 Agent 思考），则保留 `MemoryActor`。

- **Actor**: `capabilities_actor/memory_actor.py`
- **Capabilities**: `capabilities/llm_memory/manager.py` (UnifiedMemoryManager)

**交互设计**：

Python

```
# capabilities_actor/memory_actor.py

class MemoryActor(Actor):
    def __init__(self):
        from capabilities.llm_memory.manager import UnifiedMemoryManager
        self.manager = UnifiedMemoryManager() # 这一步会初始化向量库连接

    def receiveMessage(self, msg, sender):
        if isinstance(msg, StoreMemoryRequest):
            # 异步存储：Agent 发完就不管了，Actor 慢慢存
            self.manager.add_memory_intelligently(
                content=msg.content,
                context=msg.context
            )
        elif isinstance(msg, RetrieveMemoryRequest):
            # 同步检索：Agent 需要等结果
            results = self.manager.build_execution_context(msg.query)
            self.send(sender, MemoryResponse(data=results))
```



#### 4. 优化与聚合：TaskGroupAggregatorActor $\leftrightarrow$ Optimization



这是高阶功能。Actor 负责协调 N 个任务，Capability 负责计算“怎么调参最好”。

- **Actor**: `capabilities_actor/task_group_aggregator_actor.py`
- **Capabilities**: `capabilities/optimization/optuna_optimizer.py` (假设在此处)

**交互流程**：

1. **Input**: `TaskGroupRequest` 包含 10 个子任务，策略为 `optuna`。
2. **Actor**:
   - 实例化 `OptunaOptimizer`。
   - **Call 1**: `optimizer.suggest_params()` 获取第一组参数。
   - **Spawn**: 发送任务给 `ExecutionActor` 执行。
   - **Wait**: 等待结果。
3. **Feedback Loop**:
   - 收到 `TaskResult`。
   - **Call 2**: `optimizer.report_result(score=result.accuracy)`。
   - **Loop**: 优化器根据反馈生成下一组参数。
4. **Finish**: 优化器判断收敛，Actor 返回最佳结果。

------



### 三、 具体的接口定义建议



为了让这两层严丝合缝，你需要规范 `Capabilities` 层基类的接口。

**在 `capabilities/capability_base.py` 中：**

Python

```
class CapabilityBase(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """所有能力必须实现的核心执行方法，供 Actor 调用"""
        pass

    @abstractmethod
    def validate_params(self, params: Dict) -> bool:
        """Actor 在执行前可以使用此方法进行快速校验"""
        pass
```



### 四、 总结这一层的修改清单



1. **`capabilities_actor/init.py`**:
   - 确保导出的 Actor 类都是干净的 Wrapper，不包含复杂的业务逻辑代码。
2. **`capabilities_actor/execution_actor.py`**:
   - 删除对 `UniversalConnectorOrchestrator` Actor 的引用。
   - 增加对 `capabilities.connectors.connector_manager.UniversalConnectorManager` 类的引用。
   - 增加对 `capabilities.routing.context_resolver.ContextResolver` 的引用。
3. **`capabilities/connectors/`**:
   - 将 `UniversalConnectorOrchestrator` 代码迁移至此，改名为 `ConnectorManager`，去掉 Thespian 依赖，改为纯类。
4. **`capabilities/registry.py`**:
   - 确保它能以单例模式运行，并且能在 Actor 进程中正确初始化（例如：数据库连接池在 fork 后需要重建，这点在 Actor 模型中很重要）。



### 现在的系统全景图



- **User** $\rightarrow$ **RouterActor**
- **RouterActor** $\rightarrow$ **AgentActor** (大脑，决策)
- **AgentActor** $\rightarrow$ **ExecutionActor** (工头)
- **ExecutionActor** $\rightarrow$ **Capabilities (Classes)** (工人)
  - $\rightarrow$ `ConnectorManager` $\rightarrow$ Dify/API
  - $\rightarrow$ `DataAccessor` $\rightarrow$ MySQL
  - $\rightarrow$ `MemoryManager` $\rightarrow$ VectorDB

这样设计，数据流（Data Flow）清晰，且 Actor 层只负责“并发调度”和“容错”，Capabilities 层只负责“业务实现”。


#### 第五部分：common与Capabilities架构调整

这是一个非常关键的环节。要将任务的**初始（草稿态）**、**流转（执行态）**和**聚合（完成态）**串联起来，我们需要在 `Common` 层定义清晰的“血液”（Message），并在 Actor 之间建立严密的“血管”连接。

你关心的**草稿（Conversation Draft）**与**正式任务（Task）**的区别是系统体验流畅度的关键。

以下是针对你要求的 **任务全生命周期** 的详细交互设计与数据流转方案。

------



### 一、 核心数据载体设计 (`Common/Messages` & `Common/Draft`)



我们首先定义数据包。在 `common` 文件夹下，我们需要确保以下对象的定义是支撑整个流程的。



#### 1. `TaskDraft` (草稿 - 暂存态)



位于 common/draft/task_draft.py。

它不是 Message，而是持久化在 Redis 或内存中的状态对象。

Python

```
@dataclass
class TaskDraft:
    user_id: str
    intent_type: str          # 用户想干什么 (e.g., "query_sales")
    collected_params: Dict    # 已收集的参数 (e.g., {"region": "north"})
    missing_params: List[str] # 缺少的参数 (e.g., ["date"])
    status: str               # "COLLECTING", "READY", "ABORTED"
```



#### 2. 消息定义 (流转态)



位于 `common/messages/task_messages.py` 和 `agent_messages.py`。

- **`UserRequestMessage`**: 用户 -> Router -> Agent
- **`TaskGroupRequest`**: Agent -> TaskGroupAggregator (包含一组子任务)
- **`AgentTaskMessage`**: Aggregator -> ExecutionActor (单任务指令)
- **`TaskExecutionResult`**: ExecutionActor -> Aggregator -> Agent (结果)

------



### 二、 详细流程交互设计 (Step by Step)





#### 阶段 1：对话与草稿 (流程 ① - ③)



**目标**：处理多轮对话，直到信息收集完整，将“草稿”转正为“任务”。

**涉及模块**：

- **Actor**: `Agents/agent_actor.py`
- **Common**: `draft/conversation_manager.py`, `intent/intent_router.py`

**代码逻辑与数据流**：

Python

```
# agents/agent_actor.py

def _handle_user_request(self, msg, sender):
    user_id = msg.user_id
    content = msg.content
    
    # [流程 ①] 草稿判断
    # 这一步不涉及 Actor 通信，直接调用 Common 组件
    # ConversationManager 内部会去查 Redis/Memory 看有没有未完成的草稿
    draft_result = self.conversation_manager.process_user_input_complete(
        user_id=user_id, 
        user_input=content
    )
    
    # 情况 A: 还在收集参数 (Draft)
    if draft_result.status == "COLLECTING":
        # 直接回复用户，请求更多信息
        self.send(sender, SimpleMessage(content=draft_result.next_question))
        return

    # 情况 B: 草稿完成 或 新任务 (Ready)
    # [流程 ②] 意图最终确认 (如果草稿完成了，intent就是草稿的intent)
    final_intent = draft_result.intent or self.intent_router.classify(content)
    
    # [流程 ③] 任务操作判断 & 实例化
    # 将 Draft 转为正式 Task 对象
    new_task = self.task_registry.create_task(
        description=content,
        params=draft_result.collected_params, # 注入收集到的参数
        intent=final_intent
    )
    
    # 此时，Draft 生命周期结束，Task 生命周期开始
    self.conversation_manager.clear_draft(user_id)
    
    # 进入后续流程
    self._process_new_task(new_task, sender)
```



#### 阶段 2：规划与分发 (流程 ④ - ⑦)



**目标**：将一个大任务拆解，并打包发给聚合器。

**涉及模块**：

- **Actor**: `Agents/agent_actor.py`
- **Capabilities**: `decision/task_planner.py` (规划能力), `routing/task_router.py` (路由能力)

**代码逻辑与数据流**：

Python

```
# agents/agent_actor.py

def _process_new_task(self, task, sender):
    # [流程 ④] 循环检测 (略)
    
    # [流程 ⑤] 能力路由
    # 判断是自己执行(叶子)还是分发(节点)
    routing_info = self.task_router.select_best_actor(task.description)
    
    if routing_info.is_complex_task:
        # [流程 ⑥] 任务规划
        # 生成子任务列表 List[TaskSpec]
        subtasks_specs = self.task_planner.generate_plan(
            task=task,
            context=self.memory_actor.get_context() # 获取必要的背景信息
        )
        
        # [流程 ⑦] 任务分发 -> 发给 TaskGroupAggregatorActor
        # 创建聚合器 Actor (临时的)
        aggregator = self.createActor(TaskGroupAggregatorActor)
        
        # 构造 GroupRequest 消息
        group_msg = TaskGroupRequest(
            parent_task_id=task.id,
            subtasks=subtasks_specs,
            strategy="optuna", # [流程 ⑨] 的伏笔
            original_sender=sender, # 让聚合器知道最后结果给谁
            context=task.params # 传递上下文参数
        )
        
        self.send(aggregator, group_msg)
        
    else:
        # 如果是单任务，直接去流程 ⑩
        self._execute_leaf_node(task, sender)
```



#### 阶段 3：聚合与优化 (流程 ⑧ - ⑨)



**目标**：管理并发执行，并进行参数优化。

**涉及模块**：

- **Actor**: `Capabilities Actor/task_group_aggregator_actor.py`
- **Capabilities**: `parallel/optuna_optimizer.py`

**代码逻辑与数据流**：

Python

```
# capabilities_actor/task_group_aggregator_actor.py

def receiveMessage(self, msg, sender):
    if isinstance(msg, TaskGroupRequest):
        self.parent_sender = msg.original_sender
        self.pending_tasks = msg.subtasks
        self.results = []
        
        # [流程 ⑨] 并行执行判断 & 优化
        if msg.strategy == "optuna":
            # 使用 Capability 中的优化器
            from capabilities.parallel.optuna_optimizer import OptunaOptimizer
            self.optimizer = OptunaOptimizer()
            # 优化器可能会调整子任务的参数或顺序
            optimized_tasks = self.optimizer.optimize_batch(msg.subtasks)
            self._dispatch_batch(optimized_tasks)
        else:
            self._dispatch_batch(msg.subtasks)

def _dispatch_batch(self, tasks):
    # 批量发送给 ExecutionActor
    for task_spec in tasks:
        # 获取或创建执行者
        executor = self.createActor(ExecutionActor)
        
        # 构造 AgentTaskMessage
        task_msg = AgentTaskMessage(
            task_id=task_spec.id,
            task_type="LEAF",
            content=task_spec.description,
            context=task_spec.params, # 继承父级参数
            execution_mode="standard",
            sender_addr=self.myAddress # 关键：让执行者回消息给我！
        )
        
        self.send(executor, task_msg)
```



#### 阶段 4：执行与参数解析 (流程 ⑩ - ⑪)



**目标**：真正的干活，处理参数缺失。

**涉及模块**：

- **Actor**: `Capabilities Actor/execution_actor.py`
- **Capabilities**: `routing/context_resolver.py`, `registry.py`

**代码逻辑与数据流**：

Python

```
# capabilities_actor/execution_actor.py

def receiveMessage(self, msg, sender):
    if isinstance(msg, AgentTaskMessage):
        # [流程 ⑪ - 前置] 参数解析
        # 这一步是从自然语言 -> 函数参数的关键
        from capabilities.routing.context_resolver import ContextResolver
        resolver = ContextResolver()
        
        # 解析：结合当前msg.content 和 msg.context
        resolved = resolver.resolve(
            instruction=msg.content,
            provided_context=msg.context
        )
        
        # 如果参数缺失，这里其实应该抛出 NEED_MORE_INFO，或者尝试默认值
        # 这里假设解析成功
        
        # [流程 ⑪ - 执行] 调用具体能力
        try:
            # 从 Registry 获取函数/连接器
            if msg.execution_mode == "connector":
                # 调用 ConnectorManager (Capabilities层)
                from capabilities.connectors.connector_manager import UniversalConnectorManager
                result_data = UniversalConnectorManager().execute(...)
            else:
                # 调用本地能力
                func = self.capability_registry.get_capability(resolved.tool_name)
                result_data = func(**resolved.params)
            
            # 返回结果
            response = TaskExecutionResult(
                task_id=msg.task_id,
                status="SUCCESS",
                result_data=result_data
            )
            self.send(sender, response)
            
        except Exception as e:
            # 发送失败消息
            self.send(sender, TaskExecutionResult(status="FAILED", error_msg=str(e)))
```



#### 阶段 5：结果回传与事件 (流程 ⑪ - ⑫)



**目标**：层层上报，通知系统。

**涉及模块**：

- **Actor**: `TaskGroupAggregatorActor`, `AgentActor`
- **External**: `EventBus`

**代码逻辑与数据流**：

1. **ExecutionActor** 发送 `TaskExecutionResult` 给 **TaskGroupAggregatorActor**。
2. **TaskGroupAggregatorActor** 收集结果：
   - 如果是 Optuna 模式，将结果反馈给 Optimizer (`optimizer.report(result)`)，看是否需要下一轮。
   - 如果所有子任务完成，进行聚合（MapReduce / Summary）。
3. **TaskGroupAggregatorActor** 发送最终结果给 **AgentActor**。

Python

```
# agents/agent_actor.py

def _finalize_aggregation(self, parent_task_id, final_result):
    # [流程 ⑫] 事件通知
    # 调用 External/EventBus
    from external.event_bus import event_bus
    event_bus.publish_task_event(
        task_id=parent_task_id,
        event_type="TASK_COMPLETED",
        source="AgentActor",
        data=final_result
    )
    
    # [流程 ⑫] 返回给用户
    self.send(self.original_user_addr, SimpleMessage(content=final_result))
    
    # 写入记忆
    self.memory_actor.store_long_term(f"任务 {parent_task_id} 完成，结果：{final_result}")
```

------



### 三、 总结：模块间的数据流



1. **用户输入** (String) $\rightarrow$ `AgentActor`
2. `AgentActor` $\leftrightarrow$ `ConversationManager` (Draft Object)
   - *数据流*：字符串 $\rightarrow$ 结构化 Draft $\rightarrow$ Task Object
3. `AgentActor` $\rightarrow$ `TaskPlanner` (List[TaskSpec])
4. `AgentActor` $\rightarrow$ `TaskGroupAggregator` (Message: `TaskGroupRequest`)
5. `TaskGroupAggregator` $\rightarrow$ `ExecutionActor` (Message: `AgentTaskMessage`)
6. `ExecutionActor` $\leftrightarrow$ `ContextResolver` (ResolvedParams)
7. `ExecutionActor` $\rightarrow$ `CapabilityRegistry/Connector` (Result Data)
8. `ExecutionActor` $\rightarrow$ `TaskGroupAggregator` (Message: `TaskExecutionResult`)
9. `TaskGroupAggregator` $\rightarrow$ `AgentActor` (Message: `TaskResult`)
10. `AgentActor` $\rightarrow$ `EventBus` & User

通过这套设计，**草稿**处理了对话的连续性，**任务消息**处理了执行的异步性，**Common层**定义了所有标准，**Capabilities层**提供了实实在在的算法和工具。这就是你要的细致统合方案。


#### 第六部分：external架构调整

这一层是系统的**基石（Infrastructure Layer）**。它的核心职责是**屏蔽底层技术细节**，为上层的 `Agents` 和 `Capabilities` 提供统一的 I/O 接口。

你现有的 `External` 设计非常全面，但存在**过度抽象（Over-Engineering）**的问题。例如，`business_data`、`database`、`internal_storage` 三者在功能上高度重叠，会导致上层不知道该存哪里。

针对你的 **12步流程** 和 **Actor 交互需求**，我为你重新梳理了 `External` 层的架构。我们将它精简为**四大支柱**：**Clients (连接器)**、**Repositories (仓储)**、**MessageQueue (消息队列)** 和 **Storage (文件存储)**。

------



### 一、 核心调整方案 (Refactoring Strategy)



1. **合并数据库访问**：
   - 废除 `business_data` 和 `internal_storage` 的独立分类。
   - 统一为 **`database`** (存放驱动/连接池) 和 **`repositories`** (存放业务对象的持久化逻辑)。
2. **明确 API 边界**：
   - 将 `execution_connectors` 重命名为 **`clients`**。这里只放**纯粹的 API 客户端**（如 `DifyClient`），不包含复杂的编排逻辑（编排逻辑去 `Capabilities` 层）。
3. **强化 Redis 地位**：
   - 为了支持 **流程 ① 草稿判断** 和 **Actor 寻址**，Redis 必须是一等公民，不仅是 Cache，更是 State Store。

------



### 二、 详细模块设计与交互





#### 1. `database/` - 纯粹的驱动层



只负责连上数据库，不负责业务逻辑。

- **`connection_pool.py`**: 管理 MySQL/PostgreSQL 连接池。
- **`redis_client.py`**: 封装 Redis 连接，提供 `get`, `set`, `expire` 等基础方法。
- **`neo4j_client.py`**: 封装 Neo4j Driver。



#### 2. `repositories/` - 业务数据的家 (关键修改)



这是连接 `Common/Tasks`、`Common/Draft` 和 `Agents` 的桥梁。

- **`task_repository.py`**:

  - **对接**: `TaskRegistry` (Common)

  - **功能**: 保存 `Task` 对象的状态流转（CREATED -> RUNNING -> COMPLETED）。

  - **交互**:

    Python

    ```
    # External
    class TaskRepository:
        def save_task(self, task: Task):
            # 将 Common 定义的 Task 对象序列化存入 MySQL/Mongo
            db.execute("INSERT INTO tasks ...", task.to_dict())
    ```

- **`draft_repository.py`** (新增，为了流程 ①):

  - **对接**: `ConversationManager` (Common)

  - **功能**: 将用户的对话草稿存入 Redis。

  - **交互**:

    Python

    ```
    # External
    class DraftRepository:
        def save_draft(self, user_id, draft: TaskDraft):
            redis_client.set(f"draft:{user_id}", draft.to_json(), ttl=3600)
    
        def get_draft(self, user_id) -> Optional[TaskDraft]:
            data = redis_client.get(f"draft:{user_id}")
            return TaskDraft.from_json(data) if data else None
    ```

- **`agent_structure_repository.py`** (原 `agent_structure`):

  - **对接**: `TreeManager` (Agents)
  - **功能**: 操作 Neo4j，维护父子关系。



#### 3. `clients/` - 外部系统的触手



这里只做 HTTP 请求的封装。

- **`dify_client.py`**:

  - **对接**: `ConnectorManager` (Capabilities)

  - **代码**:

    Python

    ```
    class DifyClient:
        def run_workflow(self, inputs: dict, api_key: str):
            return requests.post("https://api.dify.ai/...", json=inputs...)
    ```

- **`http_client.py`**: 通用的 `requests` 封装，带重试机制。



#### 4. `message_queue/` - 循环任务的心脏 (为了流程 ④)



重构原 `loop` 模块。

- **`rabbitmq_client.py`**:

  - **对接**: `LoopSchedulerActor` (Agents)

  - **功能**: 发送延迟消息。

  - **交互**:

    Python

    ```
    class RabbitMQClient:
        def publish_delayed_task(self, task_id, delay_seconds):
            # 发送到死信队列实现延迟
            channel.basic_publish(..., properties={expiration: delay_seconds*1000})
    ```

------



### 三、 完整数据流转图 (Connecting All Layers)



现在，我们将你设计的流程与 `External` 层彻底打通。



#### 场景 1：用户输入与草稿保存 (流程 ①)



- **User** -> `RouterActor` -> `AgentActor`
- `AgentActor` 调用 `ConversationManager` (Common)。
- `ConversationManager` 调用 **`DraftRepository` (External)**。
- **`DraftRepository`** 将状态写入 **Redis (External)**。
  - *数据*: `{"user_id": "u1", "intent": "query", "params": {"date": "today"}}`



#### 场景 2：任务创建与持久化 (流程 ③)



- `AgentActor` 决定创建新任务。
- `AgentActor` 调用 `TaskRegistry` (Common)。
- `TaskRegistry` 调用 **`TaskRepository` (External)**。
- **`TaskRepository`** 将任务写入 **MySQL (External)**。
  - *数据*: `INSERT INTO tasks (id, status, agent_id) VALUES (...)`



#### 场景 3：循环任务调度 (流程 ④)



- `AgentActor` 发消息给 `LoopSchedulerActor`。
- `LoopSchedulerActor` 调用 **`RabbitMQClient` (External)**。
- **`RabbitMQClient`** 发送消息到 **RabbitMQ Server**。
  - *数据*: `Payload: { "task_id": "t123", "action": "trigger" }, TTL: 3600s`



#### 场景 4：执行 Dify 工作流 (流程 ⑩-⑪)



- `ExecutionActor` 收到任务。
- `ExecutionActor` 调用 `ConnectorManager` (Capabilities)。
- `ConnectorManager` 调用 **`DifyClient` (External)**。
- **`DifyClient`** 发起 **HTTP Request** 到 Dify API。

------



### 四、 具体的代码修改建议



为了实现上述架构，请对 `External` 文件夹做如下调整：

1. **删除冗余文件**:
   - 删除 `business_data/` 文件夹（逻辑并入 `database` 或 `repositories`）。
   - 删除 `internal_storage/` 文件夹（逻辑并入 `repositories`）。
   - 删除 `execution_connectors/` 文件夹（重命名为 `clients`，并移除 Factory 模式，改用直接类调用）。
2. **新建/重构 `repositories/task_repo.py`**:

Python

```
# external/repositories/task_repo.py
from common.tasks.task import Task
from external.database.mysql_client import MySQLClient

class TaskRepository:
    def __init__(self):
        self.db = MySQLClient() # 单例模式获取连接

    def create(self, task: Task):
        sql = "INSERT INTO tasks (id, type, status, content, created_at) VALUES (%s, %s, %s, %s, %s)"
        self.db.execute_update(sql, (task.id, task.type, task.status, task.description, task.created_at))

    def update_status(self, task_id, status, result=None):
        sql = "UPDATE tasks SET status=%s, result=%s WHERE id=%s"
        self.db.execute_update(sql, (status, result, task_id))
```

1. **新建/重构 `message_queue/rabbit_publisher.py`**:

Python

```
# external/message_queue/rabbit_publisher.py
import pika

class LoopTaskPublisher:
    def __init__(self, config):
        self.conn = pika.BlockingConnection(...)
        self.channel = self.conn.channel()
        # 声明死信交换机等配置...

    def schedule_task(self, task_id, interval_seconds):
        # 发送延迟消息
        props = pika.BasicProperties(expiration=str(int(interval_seconds * 1000)))
        self.channel.basic_publish(
            exchange='loop_delay_exchange',
            routing_key='loop_task',
            body=task_id,
            properties=props
        )
```



### 总结



通过这次重构，`External` 层变得非常纯粹：

- **Common 层** 定义数据结构（DTO）。
- **External 层** 负责将这些数据结构存储到硬盘、数据库或网络。
- **Agents/Capabilities 层** 调用 External 层来保存状态或执行副作用。

现在，你的数据流转是闭环的：

Redis (Draft) $\rightarrow$ Agent Decision $\rightarrow$ MySQL (Task) $\rightarrow$ RabbitMQ (Loop) $\rightarrow$ HTTP (Dify) $\rightarrow$ MySQL (Result)。





#### 第七部分：Entry Layerl架构调整

这是一个非常关键的收尾部分。`Entry Layer`（入口层）不仅是系统的门面，更是**同步世界（HTTP REST API）**与**异步世界（Actor System）**的转换器。

基于你提供的现有设计，最大的缺失在于**对话交互（Chat）**的接口定义，以及**查询（Query）**与**命令（Command）**处理逻辑的混淆。

为了实现高效的对外服务，我们需要采用 **CQRS（命令查询职责分离）** 的思想：

1. **写/执行操作（Command）**：通过 Actor 系统处理（如对话、创建任务）。
2. **读操作（Query）**：直接读取数据库/仓库（如查询任务进度、列表），**不要去打扰 Actor**。

以下是针对 `Entry Layer` 的详细修改和交互设计方案。

------



### 一、 API 路由设计重构 (`api_server.py`)



我们需要补充对话接口，并明确各类接口的性质。



#### 1. 新增：对话服务 (Conversational Service)



这是触发你设计的 **流程 ① (草稿)** 和 **流程 ② (意图)** 的唯一入口。

- `POST /api/v1/chat/completions`: 发送对话消息（兼容 OpenAI 格式）。
  - *Input*: `{"messages": [{"role": "user", "content": "帮我查下..."}], "stream": true}`
  - *Logic*: 触发 AgentActor 的 `_handle_user_request`。
- `POST /api/v1/chat/clear`: 清空当前会话/草稿。



#### 2. 优化：查询服务 (Query Service)



这些接口应直接读取 `External/Repositories`，保证毫秒级响应。

- `GET /api/v1/tasks`: 获取任务列表。
- `GET /api/v1/tasks/{task_id}`: 获取任务详情。
- `GET /api/v1/tasks/{task_id}/timeline`: 获取执行路径/进度（原 `execution-path`）。
- `GET /api/v1/tasks/{task_id}/artifacts`: 获取任务生成的产物（文件、图表）。



#### 3. 保持：控制服务 (Control Service)



这些接口需要修改 Actor 的状态。

- `POST /api/v1/tasks/{task_id}/command`: 发送控制指令（暂停/恢复/取消）。
- `POST /api/v1/tasks/{task_id}/feedback`: 人工反馈/评论（用于 Human-in-the-loop）。

------



### 二、 核心模块深度交互设计





#### 1. `request_handler.py` - 双模处理器



这个类是核心，需要拆分为两个处理通道：**Actor通道** 和 **Repository通道**。

Python

```
# entry_layer/request_handler.py
import uuid
from thespian.actors import ActorSystem
from common.messages.base_message import UserRequestMessage
from external.repositories.task_repo import TaskRepository
from external.repositories.draft_repo import DraftRepository

class RequestHandler:
    def __init__(self, tenant_router):
        self.tenant_router = tenant_router
        self.actor_system = ActorSystem()
        
        # 初始化仓库 (用于读操作)
        self.task_repo = TaskRepository()
        self.draft_repo = DraftRepository()

    # --- 通道 A: Command (写/交互) -> 走 Actor ---
    def handle_chat_request(self, user_id, tenant_id, content, stream=False):
        """
        处理对话请求：HTTP -> RouterActor -> AgentActor
        """
        # 1. 获取 RouterActor 地址
        router_addr = self.tenant_router.get_router_actor(tenant_id)
        
        # 2. 构造消息
        msg = UserRequestMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            content=content,
            stream=stream
        )
        
        # 3. 发送并等待 (ask)
        # 注意：这里使用 ask() 同步等待 Actor 返回结果
        # 如果是流式 (Stream)，这里需要特殊处理 (SSE)，暂按非流式处理
        response = self.actor_system.ask(router_addr, msg, timeout=30)
        
        if response is None:
            raise TimeoutError("Agent 响应超时")
            
        return response

    # --- 通道 B: Query (读) -> 走 Repository ---
    def handle_get_task_list(self, user_id, page=1, size=20):
        """
        直接查库，不打扰 Actor
        """
        return self.task_repo.list_tasks(user_id, page, size)

    def handle_get_task_detail(self, task_id):
        # 聚合多个 Repo 的数据
        task_info = self.task_repo.get_by_id(task_id)
        # 也许还需要查一下子任务的情况
        subtasks = self.task_repo.get_subtasks(task_id)
        return {**task_info, "subtasks": subtasks}
```



#### 2. `tenant_router.py` - 寻址器



你需要确保能正确找到对应租户的 `RouterActor`。

Python

```
# entry_layer/tenant_router.py

class TenantRouter:
    def get_router_actor(self, tenant_id):
        """
        根据租户ID获取全局唯一的 RouterActor 地址
        通常这个地址存储在 Redis 中，或者通过 ActorSystem 的 globalName 获取
        """
        # 假设所有 RouterActor 注册时都用了 "Router_{tenant_id}" 的别名
        return ActorSystem().createActor(
            'agents.router_actor.RouterActor',
            globalName=f"Router_{tenant_id}"
        )
```

------



### 三、 完整数据流转示例



让我们看看现在的 API 是如何驱动整个系统的。



#### 场景 1：用户发起对话（触发草稿/任务）



1. **Request**: `POST /api/v1/chat/completions` (Body: "帮我分析下上个月的销售数据")
2. **API Server**: 鉴权通过，提取 `user_id="u1"`, `tenant_id="t1"`。
3. **RequestHandler**:
   - 调用 `tenant_router.get_router_actor("t1")`。
   - 发送 `UserRequestMessage` 给 `RouterActor`。
4. **RouterActor** $\rightarrow$ **AgentActor**:
   - **AgentActor** 执行流程 ① (草稿判断)。
   - 发现信息不全（缺“上个月”的具体定义），返回 `SimpleMessage("是指10月份吗？")`。
5. **RequestHandler**: 收到 Actor 回复。
6. **Response**: HTTP 200 `{"role": "assistant", "content": "是指10月份吗？"}`。



#### 场景 2：用户确认并触发执行



1. **Request**: `POST /api/v1/chat/completions` (Body: "是的")
2. **RequestHandler** $\rightarrow$ **AgentActor**:
   - **AgentActor** 执行流程 ③ (新任务)。
   - 创建任务，写入 **MySQL** (通过 `TaskRepository`)。
   - 开始异步执行 (流程 ⑤-⑩)。
   - **立即返回**：`SimpleMessage("好的，任务已创建 (ID: t-1001)，正在分析中...")`。
3. **Response**: HTTP 200 `{"content": "好的...", "task_id": "t-1001"}`。



#### 场景 3：前端轮询任务状态



1. **Request**: `GET /api/v1/tasks/t-1001/progress`
2. **RequestHandler**:
   - **不调用 Actor**。
   - 直接调用 `TaskRepository.get_progress("t-1001")`。
   - 数据库中可能有 `task_events` 表记录了最新的 Event。
3. **Response**: HTTP 200 `{"status": "RUNNING", "progress": 45, "current_step": "Data Query"}`。

------



### 四、 针对 `api_server.py` 的具体代码调整



请在 `_register_routes` 中添加以下路由组：

Python

```
# entry_layer/api_server.py

def _register_routes(self):
    # ... 原有路由 ...

    # === 对话路由 (Command) ===
    @self.app.post("/api/v1/chat/completions")
    async def chat_completions(
        request: ChatRequest, 
        auth: AuthInfo = Depends(get_current_auth_info)
    ):
        # 异步调用 RequestHandler (虽然它是同步的，但在 FastAPI 中可以用 run_in_executor 优化)
        response = await self.request_handler.handle_chat_request(
            user_id=auth.user_id,
            tenant_id=auth.tenant_id,
            content=request.messages[-1].content
        )
        return response

    # === 任务查询路由 (Query) ===
    @self.app.get("/api/v1/tasks/{task_id}")
    async def get_task_detail(
        task_id: str, 
        auth: AuthInfo = Depends(get_current_auth_info)
    ):
        return self.request_handler.handle_get_task_detail(task_id)
```



### 总结



对外服务层设计的核心在于**“不阻塞”**和**“读写分离”**：

1. **对话**：通过 Actor 实时交互，处理草稿和意图。
2. **执行**：一旦任务建立，Actor 在后台跑，API 立即返回 Task ID。
3. **查询**：通过直接查库来跟踪后台 Actor 的进度，保证前端页面刷新的流畅性。



#### 第七部分：Envent架构调整

这是系统闭环的最后一公里。

为了满足**“汇聚在一起以供查询”**的需求，目前的 Event 设计有一个**致命弱点**：它依赖于内存 (`_store_event` 中的列表)，这意味着系统重启数据就丢了，而且 Entry Layer 的 API 很难跨进程去查询 Actor 内存里的历史数据。

我们需要将 Event 系统从 **“简单的消息通知”** 升级为 **“持久化的事件溯源 (Event Sourcing) 系统”**。

核心变革：**EventActor 不再是事件的终点，而是事件的“搬运工”，它负责将瞬时消息搬运到持久化存储（Database）中。**

以下是重构后的设计方案。

------



### 1. 架构调整概览



- **旧模式**：Agent -> EventBus -> EventActor (存内存) -> API Query (难)
- **新模式**：
  1. **写入**：Agent -> EventBus (Helper) -> `EventActor` -> **`EventRepository`** -> MySQL/NoSQL
  2. **查询**：API Server -> **`EventRepository`** -> MySQL/NoSQL -> User

------



### 2. 模块详细重构





#### 2.1 `event_types.py` (保持并增强)



保留枚举，但增加结构化定义，确保存入数据库时格式统一。

Python

```
# external/event/event_types.py
from enum import Enum, auto

class EventType(str, Enum):
    # 任务生命周期 (对应 Timeline 展示)
    TASK_CREATED = "TASK_CREATED"
    TASK_PLANNING = "TASK_PLANNING"       # 新增：规划中
    TASK_DISPATCHED = "TASK_DISPATCHED"   # 新增：分发给子Agent
    TASK_RUNNING = "TASK_RUNNING"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    
    # 调试/监控
    AGENT_THINKING = "AGENT_THINKING"     # 记录 Agent 的思考过程 (CoT)
    TOOL_CALLED = "TOOL_CALLED"           # 记录工具调用输入
    TOOL_RESULT = "TOOL_RESULT"           # 记录工具调用输出

    # ... 其他保持不变 ...
```



#### 2.2 `event_message.py` (新增/标准化)



在 `Common/Messages` 中定义标准事件体，作为数据库存储的映射对象。

Python

```
# common/messages/event_message.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

@dataclass
class SystemEventMessage:
    event_id: str
    trace_id: str             # 关键：用于追踪整个调用链 (Task ID)
    event_type: str
    source_component: str     # 哪个 Actor 发出的
    content: Dict[str, Any]   # 具体的事件数据 (参数、结果、错误堆栈)
    timestamp: float          # Unix timestamp
    level: str = "INFO"       # INFO, WARN, ERROR
```



#### 2.3 `event_actor.py` (核心枢纽)



**重大变更**：移除内存存储逻辑，接入 `EventRepository`。

Python

```
# external/event/event_actor.py
from thespian.actors import Actor
from external.repositories.event_repo import EventRepository # 新增的仓库
from common.messages.event_message import SystemEventMessage

class EventActor(Actor):
    def __init__(self):
        super().__init__()
        # 初始化持久化仓库
        self.repo = EventRepository()
        # 初始化实时推送 (可选，例如通过 WebSocket 推给前端)
        # self.socket_server = ... 

    def receiveMessage(self, msg, sender):
        if isinstance(msg, SystemEventMessage):
            # 1. 持久化 (必须)
            # 这是一个异步写操作，可以用线程池优化，避免阻塞 Actor
            self._persist_event(msg)
            
            # 2. 实时分发 (可选)
            # self._push_to_websocket(msg)

    def _persist_event(self, event: SystemEventMessage):
        try:
            self.repo.save(event)
        except Exception as e:
            # 记录日志，但不要让 EventActor 崩溃
            print(f"Failed to save event: {e}")
```



#### 2.4 `event_bus.py` (客户端工具)



**定位变更**：它不再维护订阅者列表，而是作为一个**轻量级的 SDK**，方便系统中的任何地方（Agent, Capability, Entry）快速发送事件给 `EventActor`。

Python

```
# external/event/event_bus.py
from thespian.actors import ActorSystem
from common.messages.event_message import SystemEventMessage
import time
import uuid

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance.system = ActorSystem()
            # 获取全局 EventActor 地址
            cls._instance.event_actor = cls._instance.system.createActor(
                'external.event.event_actor.EventActor',
                globalName='GlobalEventActor'
            )
        return cls._instance

    def publish(self, trace_id: str, event_type: str, source: str, data: dict, level: str="INFO"):
        """
        全系统通用的埋点方法
        """
        msg = SystemEventMessage(
            event_id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type=event_type,
            source_component=source,
            content=data,
            timestamp=time.time(),
            level=level
        )
        # Fire and Forget (不等待回执)
        self.system.tell(self.event_actor, msg)

# 全局单例导出
event_bus = EventBus()
```

------



### 3. 新增模块：`event_repository.py`



这是为了满足你“**汇聚以供查询**”的核心需求。把这个文件放在 `External/Repositories` 下。

Python

```
# external/repositories/event_repo.py
from external.database.mysql_client import MySQLClient
# 或者使用 MongoDB，因为 Event 的 content 结构多变，NoSQL 更适合
# from external.database.mongo_client import MongoClient 

class EventRepository:
    def __init__(self):
        self.db = MySQLClient()

    def save(self, event):
        """写入事件"""
        sql = """
            INSERT INTO system_events 
            (id, trace_id, event_type, source, content, created_at, level)
            VALUES (%s, %s, %s, %s, %s, FROM_UNIXTIME(%s), %s)
        """
        # content 字段建议存为 JSON 字符串
        import json
        self.db.execute_update(sql, (
            event.event_id, 
            event.trace_id, 
            event.event_type, 
            event.source_component, 
            json.dumps(event.content),
            event.timestamp,
            event.level
        ))

    def get_timeline(self, trace_id: str):
        """
        核心查询：获取某个任务的所有相关事件，按时间排序
        供 API Server 调用
        """
        sql = """
            SELECT event_type, source, content, created_at, level 
            FROM system_events 
            WHERE trace_id = %s 
            ORDER BY created_at ASC
        """
        rows = self.db.query(sql, (trace_id,))
        # 处理 rows 返回格式...
        return rows
```

------



### 4. 完整的查询流程 (The Loop Closed)



现在，我们可以回答上一节中 `Entry Layer` 留下的伏笔：`GET /api/v1/tasks/{task_id}/timeline`。

1. **执行侧 (Write)**:
   - `AgentActor` 在思考时，调用 `event_bus.publish(task_id, "AGENT_THINKING", "Agent", {"thought": "需要拆分子任务"})`。
   - `ExecutionActor` 在调用工具前后，调用 `event_bus.publish(task_id, "TOOL_CALLED", ...)`。
   - `EventActor` 收到消息，静默写入 MySQL `system_events` 表。
2. **查询侧 (Read)**:
   - 用户请求 API `GET /tasks/t-1001/timeline`。
   - `RequestHandler` 调用 `self.event_repo.get_timeline("t-1001")`。
   - `EventRepository` 执行 `SELECT ... ORDER BY created_at`。
   - 前端收到一个有序的时间轴数组，可以完美渲染出：
     - 10:00:00 - 任务创建
     - 10:00:02 - Agent 思考：需要查询数据库
     - 10:00:05 - Tool DataAccessor 被调用 (Params: SQL...)
     - 10:00:08 - Tool 返回结果 (Rows: 50)
     - 10:00:10 - 任务完成



### 总结



对 `Event` 文件夹的修改建议：

1. **`event_types.py`**: 必须保留，作为数据字典。
2. **`event_bus.py`**: 简化为发消息的 SDK，去掉复杂的订阅逻辑（因为我们主要是为了存储）。
3. **`event_actor.py`**: 改造为 **Writer**，负责对接 DB。
4. **`task_event.py` / `subscriber.py` / `publisher.py`**: **建议删除**。现在的架构很简单：生产者(Agent) -> EventBus -> EventActor -> DB。不需要复杂的观察者模式接口，因为唯一的消费者就是 DB（和可能的 WebSocket）。

这样，你的**日志汇聚**和**对外查询**功能就稳固地建立起来了。整个系统从输入到输出，再到监控，形成了一个完美的闭环。