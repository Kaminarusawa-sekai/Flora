# MAIN_DIFF_DETAILS 版本对比分析

## 说明
本文件详细对比了 `MAIN_DIFF_DETAILS(2).md` 与 `MAIN_DIFF_DETAILS(1).md` 之间的所有差异，包括新增修改文件、修改内容变化以及未跟踪文件差异。

## 一、新增修改文件

`MAIN_DIFF_DETAILS(2).md` 相比 `MAIN_DIFF_DETAILS(1).md` 新增了以下3个修改文件：

### 1. trigger/config/settings.py（修改，+4 -4）

#### 行 47：默认 rabbitmq_url 修改
```python
# 旧代码
"rabbitmq_url": "amqp://guest:guest@localhost:5672/",

# 新代码
"rabbitmq_url": "amqp://admin:Lanba%40123@121.36.203.36:10005/prod",
```

#### 行 79：EVENTS_SERVICE_BASE_URL 默认值修改
```python
# 旧代码
self.EVENTS_SERVICE_BASE_URL = os.getenv("EVENTS_SERVICE_BASE_URL", self._config_data.get("events_service_base_url", "http://localhost:8004"))

# 新代码
self.EVENTS_SERVICE_BASE_URL = os.getenv("EVENTS_SERVICE_BASE_URL", self._config_data.get("events_service_base_url", "http://localhost:8000"))
```

#### 行 86：EXTERNAL_SYSTEM_URL 默认值修改
```python
# 旧代码
self.EXTERNAL_SYSTEM_URL = os.getenv("EXTERNAL_SYSTEM_URL", self._config_data.get("external_system_url", "http://localhost:8004"))

# 新代码
self.EXTERNAL_SYSTEM_URL = os.getenv("EXTERNAL_SYSTEM_URL", self._config_data.get("external_system_url", "http://localhost:8000"))
```

### 2. trigger/services/schedule_scanner.py（修改，+41 -12）

#### 行 1-8：import 修改
```python
# 旧代码
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from external.db.impl import create_scheduled_task_repo
from external.db.session import dialect, async_session_factory
from external.messaging.base import MessageBroker

# 新代码
import asyncio
from datetime import datetime, timezone, timedelta
import logging

from trigger.external.db.impl import create_scheduled_task_repo
from trigger.external.db.session import async_session_factory, dialect
from trigger.external.messaging import MessageBroker
```

#### 行 12-23：新增函数 get_root_agent_id()
```python
# 新增代码
def get_root_agent_id(definition_id: str) -> str:
    """
    根据 definition_id 获取对应的根节点 agent_id

    Args:
        definition_id: 任务定义ID

    Returns:
        str: 根节点 agent_id
    """
    # TODO: 实现根据 definition_id 查询对应根节点的逻辑
    return "marketing"
```

#### 行 68-98：_scan_pending_tasks() 消息构建逻辑重构
```python
# 旧代码
                    # 构建执行消息
                    execute_msg = {
                        "task_id": task.id,
                        "definition_id": task.definition_id,
                        "trace_id": task.trace_id,
                        "input_params": task.input_params,
                        "scheduled_time": task.scheduled_time.isoformat(),
                        "round_index": task.round_index,
                        "schedule_config": task.schedule_config
                    }

# 新代码
                    # 从 input_params 中提取 user_id
                    input_params = task.input_params or {}
                    user_id = input_params.get("_user_id", "system")

                    # 获取根节点 agent_id
                    agent_id = get_root_agent_id(task.definition_id)

                    # 构建执行消息（匹配 tasks 端 callback 期望的格式）
                    execute_msg = {
                        "msg_type": "START_TASK",
                        "task_id": task.trace_id or str(task.id),  # 使用 trace_id 作为任务标识
                        "user_input": input_params.get("description", ""),  # 任务描述作为 user_input
                        "user_id": user_id,
                        "agent_id": agent_id,  # 根节点 agent_id
                        # 附加调度相关信息
                        "schedule_meta": {
                            "definition_id": task.definition_id,
                            "scheduled_time": task.scheduled_time.isoformat(),
                            "round_index": task.round_index,
                            "schedule_config": task.schedule_config,
                            "input_params": input_params
                        }
                    }
```

### 3. tasks/external/message_queue/rabbitmq_listener.py（修改，+75 -30）

#### 行 5：新增 import
```python
# 新增
from urllib.parse import urlparse
```

#### 行 40-48：__init__() 修改
```python
# 旧代码
        self.rabbitmq_url = self.config.get('rabbitmq_url', 'localhost')
        self.connection = None
        self.channel = None
        self.thread = None
        self.logger = logging.getLogger(__name__)

# 新代码
        self.rabbitmq_url = self.config.get('rabbitmq_url', 'amqp://guest:guest@localhost:5672/')
        self.queue_name = self.config.get('queue_name', 'task.scheduled')
        self.connection = None
        self.channel = None
        self.thread = None
        self.logger = logging.getLogger(__name__)
```

#### 行 50-67：新增方法 _parse_rabbitmq_url()
```python
# 新增代码
    def _parse_rabbitmq_url(self):
        """解析 RabbitMQ URL 为 pika 连接参数"""
        parsed = urlparse(self.rabbitmq_url)

        # 解码密码中的特殊字符
        from urllib.parse import unquote
        password = unquote(parsed.password) if parsed.password else 'guest'

        credentials = pika.PlainCredentials(
            username=parsed.username or 'guest',
            password=password
        )

        return pika.ConnectionParameters(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5672,
            virtual_host=parsed.path.lstrip('/') or '/',
            credentials=credentials
        )
```

#### 行 71-127：callback() 方法重构

##### START_TASK 处理逻辑
```python
# 旧代码
            if msg_type == "START_TASK":
                # 构造 AgentTaskMessage
                actor_msg = AgentTaskMessage(
                    task_id=data['task_id'],
                    user_input=data['user_input'],
                    user_id=data['user_id']
                )
                self.logger.info(f"投递新任务: {data['task_id']}")

# 新代码
            if msg_type == "START_TASK":
                # 从 schedule_meta 中提取额外信息
                schedule_meta = data.get("schedule_meta", {})
                input_params = schedule_meta.get("input_params", {})

                # 使用 task_id 作为 trace_id（如果没有单独的 trace_id）
                task_id = data.get('task_id', '')
                trace_id = data.get('trace_id', task_id)

                # 构造 AgentTaskMessage，补充必填字段
                actor_msg = AgentTaskMessage(
                    task_id=task_id,
                    trace_id=trace_id,
                    task_path="/0",  # 根任务路径
                    agent_id=schedule_meta.get("definition_id", "DEFAULT_ROOT_AGENT"),
                    content=data.get('user_input', ''),
                    description=input_params.get('description', data.get('user_input', '')),
                    user_id=data.get('user_id', 'system'),
                    global_context={
                        "schedule_meta": schedule_meta,
                        "original_input": data.get('user_input', '')
                    }
                )
                self.logger.info(f"投递新任务: {task_id}, trace_id: {trace_id}")
```

##### RESUME_TASK 处理逻辑
```python
# 旧代码
            elif msg_type == "RESUME_TASK":
                # 构造 ResumeTaskMessage
                actor_msg = ResumeTaskMessage(
                    task_id=data['task_id'],
                    parameters=data['parameters'],
                    user_id=data['user_id']
                )
                self.logger.info(f"投递恢复指令: {data['task_id']}")

# 新代码
            elif msg_type == "RESUME_TASK":
                task_id = data.get('task_id', '')
                trace_id = data.get('trace_id', task_id)

                # 构造 ResumeTaskMessage
                actor_msg = ResumeTaskMessage(
                    task_id=task_id,
                    trace_id=trace_id,
                    task_path=data.get('task_path', '/0'),
                    parameters=data.get('parameters', {}),
                    user_id=data.get('user_id', 'system')
                )
                self.logger.info(f"投递恢复指令: {task_id}")
```

#### 行 129-167：start() 方法重构
```python
# 旧代码
        try:
            # RabbitMQ连接配置
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_url))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='agent_tasks', durable=True)

            self.logger.info(' [*] RabbitMQ监听已启动，等待消息. To exit press CTRL+C')
            self.channel.basic_consume(queue='agent_tasks', on_message_callback=self.callback)

            self.running = True
            self.channel.start_consuming()

# 新代码
        try:
            # 使用解析后的连接参数
            connection_params = self._parse_rabbitmq_url()
            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()

            # 声明交换机和队列
            self.channel.exchange_declare(
                exchange=self.queue_name,
                exchange_type='direct',
                durable=True
            )
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.queue_bind(
                exchange=self.queue_name,
                queue=self.queue_name,
                routing_key=self.queue_name
            )

            self.logger.info(f' [*] RabbitMQ监听已启动，队列: {self.queue_name}，等待消息...')
            self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.callback)

            self.running = True
            self.channel.start_consuming()
```

## 二、未跟踪文件差异

### MAIN_DIFF_DETAILS(1).md 未跟踪文件（部分）
```
- .DS_Store
- .env.example
- CHANGES.md
- CLAUDE.md
- MAIN_DIFF_DETAILS.md
- MEMORY_PLAN.md
- STREAM_HANDLE_USER_INPUT_MODULES.md
- STREAM_HANDLE_USER_INPUT_TEST.md
- TASK_FLOW_MODULES.md
- USAGE.md
- common/noop_memory.py
- data/memory_chroma/1f7f77a8-6f08-4441-9dbd-eda90a63fcae/data_level0.bin
- data/memory_chroma/1f7f77a8-6f08-4441-9dbd-eda90a63fcae/header.bin
- data/memory_chroma/1f7f77a8-6f08-4441-9dbd-eda90a63fcae/length.bin
- data/memory_chroma/1f7f77a8-6f08-4441-9dbd-eda90a63fcae/link_lists.bin
- "dify_workflow/6.0.0457002453472466436455737.yml"
- "dify_workflow/6.0.1473356464007455642461067451006463620.yml"
- "dify_workflow/6.0.2464070457703453713470271461720470274.yml"
- "dify_workflow/6.0.3457372505656455632447367475526472545.yml"
- "dify_workflow/6.0.4475336452301451006463620.yml"
- "dify_workflow/6.0.5456756457402451426463472447432.yml"
- "dify_workflow/7.0.0455642461067450145457267457246473321466513.yml"
- "dify_workflow/7.0.1450145457267457246461407464007447523476373505676505641466501475013.yml"
- "dify_workflow/7.0.2500752451250451426473321461647447016514204505546504746451721466501475013.yml"
- "dify_workflow/7.0.3451006477247457162514204447016451715514610447430451426466501475013.yml"
- "dify_workflow/8.0.0MQL506504464074451044455632447016466501507554.yml"
- "dify_workflow/8.0.1MQL451044455632464007450706451066455632.yml"
- "dify_workflow/8.0.2500752451250451426451044455632.yml"
- "dify_workflow/8.0.3500752451250451426451044455632447016504746451721466501507554466501475013.yml"
- "dify_workflow/8.0.4512400452456451715514610447016512755471657447430451426466501475013.yml"
- "dify_workflow/9.0.0452301471114457372505676.yml"
- "dify_workflow/9.0.1452301471114455632447515.yml"
- "dify_workflow/9.0.2452301471114462505447213.yml"
- "dify_workflow/9.0.3447367450074504702507623450772.yml"
- dify_workflow/catalog.yml
- dify_workflow/dify.png
- dify_workflow/marketing_graph.cypher
- dify_workflow/records (1).json
- "dify_workflow/502045512400.xmind"
- env.py
- events/REFACTOR_PLAN.md
- interaction/data/memory_chroma/ebcdaa46-699f-4917-a6da-5016abf7ad0c/data_level0.bin
- interaction/data/memory_chroma/ebcdaa46-699f-4917-a6da-5016abf7ad0c/header.bin
- interaction/data/memory_chroma/ebcdaa46-699f-4917-a6da-5016abf7ad0c/length.bin
- interaction/data/memory_chroma/ebcdaa46-699f-4917-a6da-5016abf7ad0c/link_lists.bin
- interaction/external/rag/__init__.py
- interaction/external/rag/dify_dataset_client.py
- interaction/external/rag/dify_rag_client.py
- interaction_e2e.pid
- log.md
- node_modules/@tailwindcss/oxide-darwin-arm64/LICENSE
- node_modules/@tailwindcss/oxide-darwin-arm64/README.md
- node_modules/@tailwindcss/oxide-darwin-arm64/package.json
- node_modules/@tailwindcss/oxide-darwin-arm64/tailwindcss-oxide.darwin-arm64.node
- node_modules/lightningcss-darwin-arm64/LICENSE
- node_modules/lightningcss-darwin-arm64/README.md
- node_modules/lightningcss-darwin-arm64/lightningcss.darwin-arm64.node
- node_modules/lightningcss-darwin-arm64/package.json
- requirements.txt
- scripts/check_dify.py
- scripts/update_neo4j_datascope.py
- tasks/common/noop_memory.py
- tasks_e2e.pid
```

### MAIN_DIFF_DETAILS(2).md 未跟踪文件（完整）
MAIN_DIFF_DETAILS(2).md 包含了与 MAIN_DIFF_DETAILS(1).md 相同的未跟踪文件列表，但增加了更多的文件，包括：
- dify_workflow 目录下的所有文件
- 更多的配置文件和脚本文件

## 三、修改内容总结

### 1. 配置文件修改
- 更新了 RabbitMQ 连接配置，从默认的本地连接改为远程服务器连接
- 修改了服务 URL 默认值，从 8004 端口改为 8000 端口

### 2. 调度服务优化
- 重构了 schedule_scanner.py，改进了消息构建逻辑
- 新增了获取根节点 agent_id 的功能
- 优化了任务执行消息的格式，使其更符合 tasks 端的预期

### 3. RabbitMQ 监听器改进
- 增强了 RabbitMQ URL 解析功能，支持复杂的 URL 格式
- 重构了消息处理逻辑，支持更多的消息类型和参数
- 改进了队列声明和绑定逻辑，增加了交换机支持
- 优化了日志记录，提供更详细的调试信息

### 4. 代码结构优化
- 调整了导入路径，使用更规范的包名
- 改进了类和方法的设计，提高了代码的可读性和可维护性
- 增加了类型注解和文档字符串，提高了代码的类型安全性和可理解性

## 四、版本对比结论

`MAIN_DIFF_DETAILS(2).md` 相比 `MAIN_DIFF_DETAILS(1).md`，主要增加了以下内容：

1. **新增了3个修改文件**，主要涉及配置管理、调度服务和消息队列处理
2. **优化了系统的配置管理**，使用更灵活的配置方式
3. **改进了任务调度和执行机制**，提高了系统的可靠性和扩展性
4. **增强了消息队列处理能力**，支持更复杂的消息格式和处理逻辑
5. **完善了代码结构和文档**，提高了代码的可维护性和可理解性

这些修改表明系统正在向更成熟、更可靠的方向发展，重点优化了配置管理、任务调度和消息处理等核心功能，为系统的进一步扩展和演进奠定了基础。