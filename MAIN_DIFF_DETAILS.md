# MAIN 分支改动清单（详细）

## 已修改 (tracked)

### events/config/settings.py
- events/config/settings.py:2 (import os) +0 -1 | - import time
- events/config/settings.py:4 (from typing import Dict, Any) +1 -0 | + from pydantic import PrivateAttr
- events/config/settings.py:27-141 (DEFAULT_CONFIG_FILE_PATH = "../event_config.json") +23 -19 | +     _observer: Observer = PrivateAttr(default=None);     _full_config_path: str = PrivateAttr(default="");     _config_data: Dict[str, Any] = PrivateAttr(default_factory=dict) | -     _observer: Observer = None;     _full_config_path: str = None;     _config_data: Dict[str, Any] = None

### events/external/db/session.py
- events/external/db/session.py:47-93 (async def get_db_session() -> AsyncSession:) +4 -1 | +         # 仅在 SQLite 下执行 PRAGMA 逻辑，其他数据库跳过;         if dialect != "sqlite":;             return | -                         print(f"❌ 添加列失败: {alter_sql} | 错误: {e}")

### front/package-lock.json
- front/package-lock.json:1-2787 ((无函数上下文)) +0 -9 | -       "peer": true,;       "peer": true,;       "peer": true,

### front/src/api/conversation.js
- front/src/api/conversation.js:3-8 (import { createSSEClient, getConversationStreamUrl } from '../utils/sse';) +1 -1 | + const API_BASE_URL = 'http://localhost:8001/v1'; | - const API_BASE_URL = 'http://localhost:8000';

### front/src/api/order.js
- front/src/api/order.js:1-9 ((无函数上下文)) +2 -1 | + const INTERACTION_API_BASE_URL = 'http://localhost:8001/v1';; const EVENTS_API_BASE_URL = 'http://localhost:8000/api/v1'; | - const API_BASE_URL = 'http://localhost:8000/v1';
- front/src/api/order.js:12-161 (import { transformTraceToDag } from '../utils/dagUtils';) +11 -11 | + async function request(url, options = {}, baseUrl = INTERACTION_API_BASE_URL) {;   const response = await fetch(`${baseUrl}${url}`, config);;   }, INTERACTION_API_BASE_URL); | - async function request(url, options = {}) {;   const response = await fetch(`${API_BASE_URL}${url}`, config);;   });

### front/src/features/ResourcePanel/index.vue
- front/src/features/ResourcePanel/index.vue:1-71 ((无函数上下文)) +14 -1 | +     <div v-if="activeTab === 'files'" class="flex items-center justify-between mb-2">;       <div class="text-xs text-gray-400">;         {{ isLoading ? 'Loading...' : 'Files' }} | - import { ref } from 'vue';
- front/src/features/ResourcePanel/index.vue:97-105 (const activeTab = ref('files');) +5 -8 | + const isLoading = ref(false);; const errorMessage = ref('');; const fileInputRef = ref<HTMLInputElement | null>(null); | - // 数据模拟; const files = ref<File[]>([;   { id: 'file-1', name: 'dataset_v1.csv', size: '24MB', updated: 'Just now' },
- front/src/features/ResourcePanel/index.vue:111-190 (const selectFile = (file: File) => {) +80 -0 | + const formatFileSize = (value: number | string | undefined) => {;   const numeric = typeof value === 'string' ? Number(value) : value;;   if (!numeric && numeric !== 0) return '-';
- front/src/features/ResourcePanel/index.vue:196-206 (const deployChanges = () => {) +7 -1 | + ; onMounted(() => {;   if (activeTab.value === 'files') { | - </script>

### front/src/utils/sse.js
- front/src/utils/sse.js:129-136 (export function createSSEClient(url, options = {}) {) +1 -1 | +   return `http://localhost:8001/v1/conversations/${sessionId}/stream`; | -   return ` http://localhost:8000/v1/conversations/${sessionId}/stream`;

### interaction/capabilities/llm/qwen_llm.py
- interaction/capabilities/llm/qwen_llm.py:8-258 (logger = logging.getLogger(__name__)) +10 -11 | +         api_key = config.get("api_key") if config else None;         if not api_key:;             import os | -         api_key = None;         if 'api_key' in config:;             api_key = config['api_key'] 

### interaction/capabilities/memory/interface.py
- interaction/capabilities/memory/interface.py:6-46 (from ..capability_base import CapabilityBase) +13 -0 | + ;     # 可选扩展：核心记忆管理（允许用户调整）;     def list_core_memories(self, user_id: str, limit: int = 50):

### interaction/capabilities/memory/mem0_memory.py
- interaction/capabilities/memory/mem0_memory.py:1-2 ((无函数上下文)) +2 -2 | + import logging; from typing import Dict, Any, Optional, List | - import logging ; from typing import Dict, Any, Optional
- interaction/capabilities/memory/mem0_memory.py:8 (from .qwen_embedding import QwenEmbedding) +1 -0 | + from interaction.external.rag import DifyRagClient
- interaction/capabilities/memory/mem0_memory.py:13-229 (logger = logging.getLogger(__name__)) +128 -5 | +         self.rag_client: Optional[DifyRagClient] = None;         self.rag_top_k = 3;         rag_config = config.get("rag", {}) | -             if not results["results"]:;                 return "暂无相关记忆。";             return "\n".join([f"- {m['memory']}" for m in results])

### interaction/capabilities/user_input_manager/common_user_input_manager.py
- interaction/capabilities/user_input_manager/common_user_input_manager.py:10-134 (logger = logging.getLogger(__name__)) +5 -2 | +         history_text = "\n".join(;             f"{turn['role']}：{turn['utterance']}" for turn in dialog_history;         ) | - {"\n".join([f"{turn['role']}：{turn['utterance']}" for turn in dialog_history])};         return enriched_input

### interaction/entry_layer/api_server.py
- interaction/entry_layer/api_server.py:9 (from collections import defaultdict) +1 -1 | + from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, status, File, UploadFile, Form | - from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, status
- interaction/entry_layer/api_server.py:19-24 (from capabilities.capability_manager import CapabilityManager) +3 -0 | + from capabilities.registry import capability_registry; from capabilities.memory.interface import IMemoryCapability; from external.rag import DifyDatasetClient
- interaction/entry_layer/api_server.py:54-59 (class ResumeTaskResponse(BaseModel):) +6 -0 | + class CoreMemoryRequest(BaseModel):;     """核心记忆设置请求模型""";     key: str = Field(..., description="核心记忆键")
- interaction/entry_layer/api_server.py:91-118 (def get_current_user(x_user_id: Optional[str] = Header(None)):) +15 -0 | + def _get_dify_dataset_client() -> DifyDatasetClient:;     api_key = os.getenv("DIFY_API_KEY");     if not api_key:
- interaction/entry_layer/api_server.py:200-292 (async def stream_conversation_events(session_id: str):) +60 -0 | + @app.get("/memory/{user_id}/core", tags=["记忆"]); async def list_core_memory(user_id: str, limit: int = 50):;     """获取用户核心记忆列表"""

### interaction/main.py
- interaction/main.py:35-37 (app.mount("/v1", api_app)) +1 -1 | +     uvicorn.run(app, host="0.0.0.0", port=8001) | -     uvicorn.run(app, host="0.0.0.0", port=8000)

### node_modules/.package-lock.json
- node_modules/.package-lock.json:1-367 ((无函数上下文)) +38 -0 | +     "node_modules/@tailwindcss/oxide-darwin-arm64": {;       "version": "4.1.18",;       "resolved": "https://registry.npmmirror.com/@tailwindcss/oxide-darwin-arm64/-/oxide-darwin-arm64-4.1.18.tgz",

### start_interaction.py
- start_interaction.py:11-17 (print(f"工作目录: {project_root}")) +2 -2 | +     "--port", "8001",; ], cwd=project_root) | -     "--port", "8000",; ], cwd=project_root)

### start_tasks.py
- start_tasks.py:11-19 (os.environ["PYTHONPATH"] = project_root) +2 -2 | +     "--port", "8002",; ], cwd=project_root) | -     "--port", "8000",; ], cwd=project_root)

### start_trigger.py
- start_trigger.py:11-17 (print(f"工作目录: {project_root}")) +7 -5 | + subprocess.run([;     sys.executable,;     "trigger/main.py", | - subprocess.run([sys.executable, ;                 "trigger/main.py";                 "--host", "0.0.0.0",

### tasks/agents/agent_actor.py
- tasks/agents/agent_actor.py:25-26 (from events.event_bus import event_bus) +1 -0 | + from common.noop_memory import NoopMemory
- tasks/agents/agent_actor.py:34-607 (logger = logging.getLogger(__name__)) +75 -7 | +             try:;                 self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability);             except Exception as e: | -             self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability);         conversation_context = self.memory_cap.build_conversation_context(self.current_user_id); 

### tasks/agents/leaf_actor.py
- tasks/agents/leaf_actor.py:8-9 (from events.event_bus import event_bus) +1 -0 | + from common.noop_memory import NoopMemory
- tasks/agents/leaf_actor.py:13-367 (logger = logging.getLogger(__name__)) +28 -4 | +             try:;                 self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability);             except Exception as e: | -             self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability);                 self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability);         from ..capability_actors.execution_actor import ExecutionActor

### tasks/agents/tree/node_service.py
- tasks/agents/tree/node_service.py:10-358 (from external.repositories.agent_structure_repo import AgentStructureRepository) +8 -2 | +                 from env import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD;                 from external.database.neo4j_client import Neo4jClient;                     neo4j_client = Neo4jClient( | -                 from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD;                     self.structure = AgentStructureRepository(

### tasks/agents/tree/relationship_service.py
- tasks/agents/tree/relationship_service.py:9-453 (from external.repositories.agent_structure_repo import AgentStructureRepository) +5 -3 | +                 from env import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD;                 from external.database.neo4j_client import Neo4jClient;                     neo4j_client = Neo4jClient( | -                 from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD;                     self.structure = AgentStructureRepository(;         self.logger.info("关系服务已关闭")

### tasks/agents/tree/tree_manager.py
- tasks/agents/tree/tree_manager.py:6-7 (from .relationship_service import RelationshipService) +1 -0 | + from env import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- tasks/agents/tree/tree_manager.py:11-502 (from external.repositories.agent_structure_repo import AgentStructureRepository) +11 -4 | +         if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:;             self.agent_structure_repo = AgentStructureRepository();         else: | -         self.agent_structure_repo = AgentStructureRepository();             return meta.get("is_leaf", False);         

### tasks/capabilities/__init__.py
- tasks/capabilities/__init__.py:1-2 ((无函数上下文)) +1 -0 | + import os
- tasks/capabilities/__init__.py:5-41 (from .registry import CapabilityRegistry) +27 -29 | + # 子模块采用延迟加载，避免在 import 时触发重初始化; _LAZY_SUBMODULES = {;     "context_resolver": ".context_resolver", | - # 导出子模块; from . import context_resolver; from . import decision
- tasks/capabilities/__init__.py:43 (_global_manager = None) +1 -1 | + CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json")) | - CONFIG_PATH = "./tasks/config.json"
- tasks/capabilities/__init__.py:87-99 (def get_capability_registry() -> CapabilityRegistry:) +1 -1 | +     return manager.get_capability(name, expected_type) | -     return manager.get_capability(name, expected_type)

### tasks/capabilities/capability_manager.py
- tasks/capabilities/capability_manager.py:12-207 (from .capbility_config import CapabilityConfig) +9 -2 | +     def __init__(self, config_path: str = None):;         if not config_path:;             config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json")) | -     def __init__(self, config_path: str = "./tasks/config.json"):;         return self.registry

### tasks/capabilities/capbility_config.py
- tasks/capabilities/capbility_config.py:13-88 (from typing import Dict, Any, Optional) +4 -2 | +     def __init__(self, config_path: str = None):;         if not config_path:;             config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json")) | -     def __init__(self, config_path: str = "./tasks/config.json"):;             self.logger.error(f"Failed to save config: {e}")

### tasks/capabilities/context_resolver/tree_context_resolver.py
- tasks/capabilities/context_resolver/tree_context_resolver.py:11-738 (logger = logging.getLogger(__name__)) +88 -7 | +             from agents.tree.tree_manager import treeManager;                 if not leaf_meta:;                     leaf_meta = self._resolve_kv_globally(query) | -             from ...agents.tree.tree_manager import treeManager;                 ;                     result[key] = leaf_meta  # 或设为 None，按需

### tasks/capabilities/excution/connect/dify_connector.py
- tasks/capabilities/excution/connect/dify_connector.py:2 (from typing import Dict, Any, List) +1 -0 | + import json
- tasks/capabilities/excution/connect/dify_connector.py:10-484 (logger = logging.getLogger(__name__)) +188 -8 | + ;         # 3. 回退到环境变量;         try: | -     def _check_missing_inputs(self, inputs: Dict[str, Any]) -> Dict[str, str]:;         required_inputs = self._get_required_inputs()  # 现在返回 {var: meta};             missing_inputs = self._check_missing_inputs(inputs)

### tasks/capabilities/llm/qwen_llm.py
- tasks/capabilities/llm/qwen_llm.py:7-256 (from .interface import ILLMCapability) +11 -12 | +         # 从配置或环境中获取参数（如果提供）;         api_key = config.get("api_key") if config else None;         if not api_key: | -         # 从配置中获取参数（如果提供）;         api_key = None;         if 'api_key' in config:

### tasks/capabilities/llm_memory/__init__.py
- tasks/capabilities/llm_memory/__init__.py:3-18 ((无函数上下文)) +14 -3 | + _LAZY_EXPORTS = {;     "UnifiedMemory": (".unified_memory", "UnifiedMemory"),;     "UnifiedMemoryManager": (".unified_manageer.manager", "UnifiedMemoryManager"), | - from .unified_memory import UnifiedMemory; from .unified_manageer.manager import UnifiedMemoryManager; from .unified_manageer.short_term import ShortTermMemory
- tasks/capabilities/llm_memory/__init__.py:20-21 (from .unified_manageer.short_term import ShortTermMemory) +1 -1 | + __all__ = list(_LAZY_EXPORTS.keys()) | - __all__ = ['UnifiedMemory', 'UnifiedMemoryManager', 'ShortTermMemory']

### tasks/capabilities/llm_memory/unified_manageer/manager.py
- tasks/capabilities/llm_memory/unified_manageer/manager.py:12-23 (from mem0 import Memory) +10 -2 | + from env import MEM0_CONFIG; _SHARED_MEM0_CLIENT = None;  | - from config import MEM0_CONFIG; SHARED_MEM0_CLIENT = Memory.from_config(MEM0_CONFIG)
- tasks/capabilities/llm_memory/unified_manageer/manager.py:33-413 (from .memory_interfaces import IVaultRepository, IProceduralRepository, IResourc) +43 -16 | +         self.mem0 = mem0_client;         self._mem0_warned = False;     def add_memory_intelligently(self, user_id, content: str, metadata: Dict = None): | -         self.mem0 = mem0_client or SHARED_MEM0_CLIENT;     def add_memory_intelligently(self,user_id,content: str):;                 "qwen", expected_type=ILLMCapability

### tasks/capabilities/llm_memory/unified_manageer/short_term.py
- tasks/capabilities/llm_memory/unified_manageer/short_term.py:5-34 (from external.memory_store.stm_dao import STMRecordDAO) +9 -1 | +     def get_history_by_scope(self, scope_prefix: str, n: int = None) -> List[Dict[str, str]]:;         n = n or self.max_history;         return self.dao.get_recent_messages_by_scope(scope_prefix, limit=n) | -         self.dao.cleanup_old_records(max_age_seconds)

### tasks/capabilities/llm_memory/unified_memory.py
- tasks/capabilities/llm_memory/unified_memory.py:12 (from .interface import IMemoryCapability) +1 -1 | + from .unified_manageer.manager import UnifiedMemoryManager, get_shared_mem0_client | - from .unified_manageer.manager import UnifiedMemoryManager, SHARED_MEM0_CLIENT
- tasks/capabilities/llm_memory/unified_memory.py:45-231 (logger = logging.getLogger(__name__)) +43 -27 | +     _state_store: Dict[str, Any] = {};         # Lazy init: defer heavy resources until first use.;         self.is_initialized = True | - ;         try:;             with self._cache_lock:

### tasks/capabilities/task_planning/__init__.py
- tasks/capabilities/task_planning/__init__.py:3-17 ((无函数上下文)) +13 -2 | + _LAZY_EXPORTS = {;     "ITaskPlanningCapability": (".interface", "ITaskPlanningCapability"),;     "CommonTaskPlanning": (".common_task_planner", "CommonTaskPlanning"), | - from .interface import ITaskPlanningCapability; from .common_task_planner import CommonTaskPlanning
- tasks/capabilities/task_planning/__init__.py:19-20 (from .common_task_planner import CommonTaskPlanning) +2 -1 | + ; __all__ = list(_LAZY_EXPORTS.keys()) | - __all__ = ['ITaskPlanningCapability', 'CommonTaskPlanning', ]

### tasks/capabilities/task_planning/common_task_planner.py
- tasks/capabilities/task_planning/common_task_planner.py:16-755 (logger = logging.getLogger(__name__)) +27 -3 | +         from agents.tree.tree_manager import treeManager;                 return [;                     { | -         from ...agents.tree.tree_manager import treeManager;                 return [];         return ""

### tasks/capabilities/text_to_sql/utils.py
- tasks/capabilities/text_to_sql/utils.py:3 (import re) +1 -1 | + from env import MIN_RESULT_ROWS, MAX_SQL_LENGTH, ALLOWED_TABLES | - from config import MIN_RESULT_ROWS, MAX_SQL_LENGTH, ALLOWED_TABLES
- tasks/capabilities/text_to_sql/utils.py:5-29 (from config import MIN_RESULT_ROWS, MAX_SQL_LENGTH, ALLOWED_TABLES) +3 -3 | +     # 2. 禁止危险关键字（使用词边界，避免误伤字段名如 deleted）;     dangerous_pattern = r"\b(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|EXEC|UNION)\b";     if re.search(dangerous_pattern, sql_upper): | -     # 2. 禁止危险关键字;     dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "EXEC", "UNION"];     if any(kw in sql_upper for kw in dangerous):
- tasks/capabilities/text_to_sql/utils.py:31-39 (def is_safe_sql(sql: str) -> bool:) +1 -1 | +     return True | -     return True

### tasks/capabilities/text_to_sql/vanna/vanna_qwen_chroma.py
- tasks/capabilities/text_to_sql/vanna/vanna_qwen_chroma.py:9 (from dashscope import Generation) +1 -1 | + from env import DASHSCOPE_API_KEY | - from config import DASHSCOPE_API_KEY
- tasks/capabilities/text_to_sql/vanna/vanna_qwen_chroma.py:15-117 (from .vanna_factory import register_vanna) +1 -1 | +     #     return sql.strip() | -     #     return sql.strip()

### tasks/capabilities/text_to_sql/vanna_text_to_sql.py
- tasks/capabilities/text_to_sql/vanna_text_to_sql.py:15-172 (from .vanna.vanna_factory import VannaFactory) +29 -13 | + from env import VANNA_TYPE;         self.db_type = db_type;         self.db_type = db_type | - from config import VANNA_TYPE;             raise ValueError("Missing 'agent_id' in config");             raise ValueError(f"Invalid database config for agent {agent_id}: {data_source}")

### tasks/capability_actors/execution_actor.py
- tasks/capability_actors/execution_actor.py:17-18 (from capabilities.excution import BaseExecution) +2 -0 | + from capabilities.llm.interface import ILLMCapability; from capabilities.llm_memory.interface import IMemoryCapability
- tasks/capability_actors/execution_actor.py:27-400 (logger = logging.getLogger(__name__)) +72 -4 | +         self._excution:BaseExecution = get_capability("excution", BaseExecution)  # 添加连接器管理器实例;         self._rewrite_running_config_with_memory(msg, running_config);  | -         self._excution:BaseExecution = get_capability("execution", BaseExecution)  # 添加连接器管理器实例; ; 

### tasks/capability_actors/mcp_actor.py
- tasks/capability_actors/mcp_actor.py:4 (import json) +1 -1 | + from typing import Any, Dict, Optional | - from typing import Any, Dict
- tasks/capability_actors/mcp_actor.py:7-14 (from capabilities.registry import capability_registry) +6 -0 | + from capabilities.llm_memory.interface import IMemoryCapability; try:;     from skills_for_all_agent.skill_tool import skill_tool, DEFAULT_SKILLS_ROOT
- tasks/capability_actors/mcp_actor.py:22-309 (from common.messages.types import MessageType) +194 -10 | +         self.skill_tool = skill_tool;         self.skills_root = DEFAULT_SKILLS_ROOT;         self.skill_index = [] | -             from ..capabilities.context_resolver.interface import IContextResolverCapbility;                 # 获取图表绘制能力;                 from ..capabilities.draw_charts.interface import IChartDrawer

### tasks/capability_actors/result_aggregator_actor.py
- tasks/capability_actors/result_aggregator_actor.py:30-549 (from common.signal.signal_status import SignalStatus) +5 -5 | +         from agents.tree.tree_manager import treeManager;                 parameters=getattr(task_spec, "parameters", {}) or {};                 from agents.leaf_actor import LeafActor | -         from ..agents.tree.tree_manager import treeManager;                 parameters={}                           # ← 留空或后续扩展;                 from ..agents.leaf_actor import LeafActor

### tasks/capability_actors/task_group_aggregator_actor.py
- tasks/capability_actors/task_group_aggregator_actor.py:33-543 (logger = logging.getLogger(__name__)) +50 -1 | +                 elif msg.status in ["NEED_INPUT"]:;                     self._handle_step_need_input(msg, sender);         root_agent_id = self._extract_root_agent_id(msg.task_path) | -         self.send(self.myAddress, ActorExitRequest())

### tasks/common/messages/task_messages.py
- tasks/common/messages/task_messages.py:81-88 (class TaskGroupRequestMessage(TaskMessage):) +1 -0 | +     params: Dict[str, Any] = Field(default_factory=dict)
- tasks/common/messages/task_messages.py:131-137 (class ExecutionResultMessage(TaskMessage):) +0 -1

### tasks/common/taskspec/task_spec.py
- tasks/common/taskspec/task_spec.py:81-149 (from pydantic import BaseModel, Field, ConfigDict) +1 -1 | +     parameters: Dict[str, Any] = Field(default_factory=dict)

### tasks/entry_layer/api_server.py
- tasks/entry_layer/api_server.py:13 (from pydantic import BaseModel) +0 -1 | - from thespian.actors import ActorSystem
- tasks/entry_layer/api_server.py:19-20 (from common.messages.task_messages import AgentTaskMessage, ResumeTaskMessage) +2 -1 | + from capabilities import init_capabilities; from capabilities.registry import capability_registry | - from agents.agent_actor import AgentActor
- tasks/entry_layer/api_server.py:33-93 (app = FastAPI() +46 -4 | + def _init_actor_system() -> None:;     """Lazy init ActorSystem to avoid heavy work at import time.""";     if getattr(app.state, "actor_system", None): | - # 1. 启动Actor系统（单例）; actor_system = ActorSystem('simpleSystemBase'); # 2. 获取AgentActor的引用
- tasks/entry_layer/api_server.py:95-265 (class TaskRequest(BaseModel):) +80 -6 | +     trace_id: str | None = None;     task_path: str | None = None;  | -             user_input=req.user_input,;             user_id=req.user_id,;             task_id=task_id
- tasks/entry_layer/api_server.py:340-363 (def create_api_server(config: dict = None) -> FastAPI:) +1 -1 | +     ) | -     )

### tasks/events/event_bus.py
- tasks/events/event_bus.py:9-10 (import uuid) +2 -0 | + import asyncio; import threading
- tasks/events/event_bus.py:17-319 (from common.signal.signal_status import SignalStatus) +45 -1 | + ;     def publish_task_event_sync(;         self, | -     

### tasks/external/__init__.py
- tasks/external/__init__.py:1-10 ((无函数上下文)) +7 -7 | + _LAZY_SUBMODULES = {;     "clients": ".clients",;     "database": ".database", | - # 导出子模块; from . import clients; from . import database
- tasks/external/__init__.py:12-21 (from . import repositories) +10 -15 | + def __getattr__(name: str):;     if name in _LAZY_SUBMODULES:;         import importlib | - __all__ = [;     # 子模块;     'clients',

### tasks/external/database/connection_pool.py
- tasks/external/database/connection_pool.py:65-130 (class BaseConnectionPool(ABC):) +1 -1 | +             from env import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_CHARSET, MYSQL_MAX_CONNECTIONS | -             from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_CHARSET, MYSQL_MAX_CONNECTIONS
- tasks/external/database/connection_pool.py:133-216 (class MySQLConnectionPool(BaseConnectionPool):) +1 -1 | +             from env import POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_USER, POSTGRESQL_PASSWORD | -             from config import POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_USER, POSTGRESQL_PASSWORD
- tasks/external/database/connection_pool.py:219-313 (class PostgreSQLConnectionPool(BaseConnectionPool):) +1 -1 | +             from env import SQLSERVER_HOST, SQLSERVER_PORT, SQLSERVER_USER, SQLSERVER_PASSWORD, SQLSERVER_DRIVER | -             from config import SQLSERVER_HOST, SQLSERVER_PORT, SQLSERVER_USER, SQLSERVER_PASSWORD, SQLSERVER_DRIVER
- tasks/external/database/connection_pool.py:316-409 (class SQLServerConnectionPool(BaseConnectionPool):) +1 -1 | +             from env import ORACLE_HOST, ORACLE_PORT, ORACLE_USER, ORACLE_PASSWORD, ORACLE_SID | -             from config import ORACLE_HOST, ORACLE_PORT, ORACLE_USER, ORACLE_PASSWORD, ORACLE_SID
- tasks/external/database/connection_pool.py:412-440 (class OracleConnectionPool(BaseConnectionPool):) +2 -2 | +     def create_pool(db_type: str, config: Optional[Dict[str, Any]] = None) -> BaseConnectionPool:;             raise ValueError(f"Unsupported database type: {db_type}") | -     def create_pool(db_type: str, config: Dict[str, Any]) -> BaseConnectionPool:;             raise ValueError(f"Unsupported database type: {db_type}")

### tasks/external/database/neo4j_client.py
- tasks/external/database/neo4j_client.py:4 (from typing import Any, List, Dict, Optional) +1 -1 | + from env import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD | - from config import NEO4J_URI , NEO4J_USER, NEO4J_PASSWORD

### tasks/external/database/redis_client.py
- tasks/external/database/redis_client.py:4 (from typing import Any, Optional) +1 -1 | + from env import REDIS_HOST, REDIS_PORT, REDIS_DATABASE, REDIS_PASSWORD | - from config import REDIS_HOST, REDIS_PORT, REDIS_DATABASE, REDIS_PASSWORD

### tasks/external/memory_store/__init__.py
- tasks/external/memory_store/__init__.py:1-13 ((无函数上下文)) +13 -9 | + _LAZY_EXPORTS = {;     "EncryptedVaultRepository": (".encrypte_vault_repository", "EncryptedVaultRepository"),;     "FileBasedProceduralRepository": (".filebased_procedural_repository", "FileBasedProceduralRepository"), | - from .encrypte_vault_repository import EncryptedVaultRepository; from .filebased_procedural_repository import FileBasedProceduralRepository; from .resource_repository import ResourceRepository
- tasks/external/memory_store/__init__.py:15-27 (from .memory_repos import build_vault_repo, build_procedural_repo, build_resourc) +13 -13 | + ; def __getattr__(name: str):;     if name in _LAZY_EXPORTS: | - __all__ = [;     'EncryptedVaultRepository',;     'FileBasedProceduralRepository',

### tasks/external/memory_store/filebased_procedural_repository.py
- tasks/external/memory_store/filebased_procedural_repository.py:2-5 (from pathlib import Path) +1 -0 | + import os
- tasks/external/memory_store/filebased_procedural_repository.py:10 (import numpy as np) +0 -1 | - from sentence_transformers import SentenceTransformer
- tasks/external/memory_store/filebased_procedural_repository.py:12-116 (from sentence_transformers import SentenceTransformer) +43 -11 | +         # 默认关闭向量模型，避免模型加载锁导致服务阻塞。;         use_embeddings = os.getenv("PROCEDURAL_USE_EMBEDDINGS", "false").lower() == "true";         self.model = None | -         ##TODO:从本地加载模型，后续待调整;         self.model = SentenceTransformer( "sentence-transformers/all-MiniLM-L6-v2",;             local_files_only=True  # 👈 确保不联网

### tasks/external/memory_store/memory_repos.py
- tasks/external/memory_store/memory_repos.py:1-19 ((无函数上下文)) +10 -10 | + from capabilities.llm_memory.unified_manageer.memory_interfaces import (;     IVaultRepository,;     IProceduralRepository, | - from capabilities.llm_memory.unified_manageer.memory_interfaces import IVaultRepository, IProceduralRepository, IResourceRepository; ; from .filebased_procedural_repository import FileBasedProceduralRepository
- tasks/external/memory_store/memory_repos.py:21-25 (def build_vault_repo() -> IVaultRepository:) +2 -0 | +     from .filebased_procedural_repository import FileBasedProceduralRepository; 
- tasks/external/memory_store/memory_repos.py:27-40 (def build_procedural_repo() -> IProceduralRepository:) +6 -2 | +     from .sqlite_resource_dao import SQLiteResourceDAO;     from .storage import get_minio_client  # ← 统一获取 MinIO 客户端;     from .resource_repository import ResourceRepository | -         local_dir=config.get("local_dir");     )

### tasks/external/memory_store/stm_dao.py
- tasks/external/memory_store/stm_dao.py:6-73 (from typing import List, Dict, Optional) +17 -1 | +     def get_recent_messages_by_scope(self, scope_prefix: str, limit: int = 10) -> List[Dict[str, str]]:;         like_pattern = f"{scope_prefix}:%";         with sqlite3.connect(self.db_path) as conn: | -             conn.execute("DELETE FROM stm_records WHERE created_at < ?", (cutoff,))

### tasks/main.py
- tasks/main.py:11-16 (import sys) +6 -0 | + import os; ; # Ensure project root is on sys.path so local config.py is used.
- tasks/main.py:115-157 (def cleanup_resources():) +1 -1 | +             # log_config=None,          # 👈 关键！禁用 uvicorn 的日志配置 | -             log_config=None,          # 👈 关键！禁用 uvicorn 的日志配置

### trigger/main.py
- trigger/main.py:109-133 (async def health_check():) +1 -1 | +             port=8003, | -             port=8001,

## 未跟踪 (untracked)
- "dify_workflow/6.0.0\345\270\202\345\234\272\346\264\236\345\257\237.yml"
- "dify_workflow/6.0.1\347\233\256\346\240\207\345\256\242\346\210\267\345\210\206\346\236\220.yml"
- "dify_workflow/6.0.2\346\240\270\345\277\203\345\237\213\347\202\271\346\217\220\347\202\274.yml"
- "dify_workflow/6.0.3\345\273\272\350\256\256\345\256\232\344\273\267\347\255\226\347\225\245.yml"
- "dify_workflow/6.0.4\347\253\236\345\223\201\345\210\206\346\236\220.yml"
- "dify_workflow/6.0.5\345\267\256\345\274\202\345\214\226\346\234\272\344\274\232.yml"
- "dify_workflow/7.0.0\345\256\242\346\210\267\345\201\245\345\272\267\345\272\246\347\233\221\346\265\213.yml"
- "dify_workflow/7.0.1\345\201\245\345\272\267\345\272\246\346\214\207\346\240\207\344\275\223\347\263\273\350\256\276\350\256\241\346\265\201\347\250\213.yml"
- "dify_workflow/7.0.2\350\207\252\345\212\250\345\214\226\347\233\221\346\216\247\344\270\216\351\242\204\350\255\246\350\247\246\345\217\221\346\265\201\347\250\213.yml"
- "dify_workflow/7.0.3\345\210\206\347\272\247\345\271\262\351\242\204\344\270\216\345\217\215\351\246\210\344\274\230\345\214\226\346\265\201\347\250\213.yml"
- "dify_workflow/8.0.0MQL\350\265\204\346\240\274\345\210\244\345\256\232\344\270\216\346\265\201\350\275\254.yml"
- "dify_workflow/8.0.1MQL\345\210\244\345\256\232\346\240\207\345\207\206\345\210\266\345\256\232.yml"
- "dify_workflow/8.0.2\350\207\252\345\212\250\345\214\226\345\210\244\345\256\232.yml"
- "dify_workflow/8.0.3\350\207\252\345\212\250\345\214\226\345\210\244\345\256\232\344\270\216\350\247\246\345\217\221\346\265\201\350\275\254\346\265\201\347\250\213.yml"
- "dify_workflow/8.0.4\351\224\200\345\224\256\345\217\215\351\246\210\344\270\216\351\227\255\347\216\257\344\274\230\345\214\226\346\265\201\347\250\213.yml"
- "dify_workflow/9.0.0\345\223\201\347\211\214\345\273\272\350\256\276.yml"
- "dify_workflow/9.0.1\345\223\201\347\211\214\345\256\232\344\275\215.yml"
- "dify_workflow/9.0.2\345\223\201\347\211\214\346\225\205\344\272\213.yml"
- "dify_workflow/9.0.3\344\273\267\345\200\274\350\247\202\350\276\223\345\207\272.yml"
- "dify_workflow/\350\220\245\351\224\200.xmind"
- .DS_Store
- .env.example
- CHANGES.md
- CLAUDE.md
- MAIN_DIFF.md
- MEMORY_PLAN.md
- USAGE.md
- common/noop_memory.py
- dify_workflow/catalog.yml
- dify_workflow/dify.png
- dify_workflow/marketing_graph.cypher
- dify_workflow/records (1).json
- env.py
- events/REFACTOR_PLAN.md
- interaction/external/rag/__init__.py
- interaction/external/rag/dify_dataset_client.py
- interaction/external/rag/dify_rag_client.py
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
