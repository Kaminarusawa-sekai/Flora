# 主分支差异清单（按文件/函数）

说明：对比基准为 `origin/main`，变更详情来自 `git diff` 的函数/上下文信息。
说明：旧/新行号范围基于当前工作区与主分支的差异。

## events/config/settings.py（修改，+24 -20）
- 位置：import os（旧行 3，新行 无）
- 位置：from typing import Dict, Any（旧行 无，新行 4）
- 位置：class Settings(BaseSettings):（旧行 51-53，新行 51-53）
- 位置：class Settings(BaseSettings):（旧行 59，新行 59）
- 位置：class Settings(BaseSettings):（旧行 61-63，新行 61-62）
- 位置：class Settings(BaseSettings):（旧行 65-66，新行 64-65）
- 位置：class Settings(BaseSettings):（旧行 69，新行 68）
- 位置：class Settings(BaseSettings):（旧行 无，新行 73-80）
- 位置：class Settings(BaseSettings):（旧行 78-82，新行 85）
- 位置：class Settings(BaseSettings):（旧行 84-85，新行 87-88）
- 位置：class Settings(BaseSettings):（旧行 88，新行 91）
- 位置：class Settings(BaseSettings):（旧行 92，新行 95-96）

## events/external/db/session.py（修改，+4 -1）
- 位置：async def create_tables():（旧行 无，新行 54-56）
- 位置：async def create_tables():（旧行 90，新行 93）

## front/package-lock.json（修改，+0 -9）
- 位置：顶层（旧行 1224，新行 无）
- 位置：顶层（旧行 1313，新行 无）
- 位置：顶层（旧行 1692，新行 无）
- 位置：顶层（旧行 1806，新行 无）
- 位置：顶层（旧行 2424，新行 无）
- 位置：顶层（旧行 2472，新行 无）
- 位置：顶层（旧行 2620，新行 无）
- 位置：顶层（旧行 2679，新行 无）
- 位置：顶层（旧行 2761，新行 无）

## front/src/api/conversation.js（修改，+1 -1）
- 位置：import { createSSEClient, getConversationStreamUrl } from '../utils/sse';（旧行 4，新行 4）

## front/src/api/order.js（修改，+13 -12）
- 位置：顶层（旧行 4，新行 4-5）
- 位置：import { transformTraceToDag } from '../utils/dagUtils';（旧行 17，新行 18）
- 位置：async function request(url, options = {}) {（旧行 34，新行 35）
- 位置：export async function sendUserMessage(sessionId, messageData) {（旧行 59，新行 60）
- 位置：export async function resumeTask(taskId, resumeData) {（旧行 74，新行 75）
- 位置：export async function listTasksInTrace(traceId, filters = {}) {（旧行 99，新行 100）
- 位置：export async function getTraceTopology(traceId) {（旧行 108，新行 109）
- 位置：export async function getTraceStatus(traceId) {（旧行 118，新行 119）
- 位置：export async function getTaskDetail(taskId, expandPayload = false) {（旧行 128，新行 129）
- 位置：export async function getReadyTasks() {（旧行 136，新行 137）
- 位置：export async function getTraceDetail(traceId, expandPayload = false) {（旧行 146，新行 147）
- 位置：export async function getLatestTraceByRequest(requestId) {（旧行 155，新行 156）

## front/src/composables/useApi.js（修改，+19 -9）
- 位置：顶层（旧行 1，新行 1）
- 位置：export function useApi() {（旧行 22，新行 22）
- 位置：export function useConversationSSE(sessionId, options = {}) {（旧行 28-30，新行 28-35）
- 位置：export function useConversationSSE(sessionId, options = {}) {（旧行 无，新行 62-70）
- 位置：export function useConversationSSE(sessionId, options = {}) {（旧行 68-71，新行 无）

## front/src/features/Copilot/index.vue（修改，+93 -14）
- 位置：顶层（旧行 41，新行 41）
- 位置：顶层（旧行 无，新行 104-111）
- 位置：const showScrollToBottom = ref(false);（旧行 222，新行 230）
- 位置：const currentAIMessage = ref(null);（旧行 无，新行 232-235）
- 位置：const renderMarkdown = (text) => {（旧行 无，新行 253-296）
- 位置：const {（旧行 248，新行 304）
- 位置：const {（旧行 250，新行 306）
- 位置：const {（旧行 无，新行 312-319）
- 位置：const {（旧行 无，新行 340-341）
- 位置：const {（旧行 无，新行 351-352）
- 位置：const {（旧行 无，新行 375-376）
- 位置：const {（旧行 无，新行 385-386）
- 位置：onUnmounted(() => {（旧行 无，新行 414）
- 位置：watch(sessionId, async (newSessionId) => {（旧行 356，新行 429）
- 位置：const fetchSessionHistory = async () => {（旧行 381，新行 454）
- 位置：const fetchSessionHistory = async () => {（旧行 无，新行 459）
- 位置：const fetchSessionHistory = async () => {（旧行 395，新行 无）
- 位置：onMounted(async () => {（旧行 402-408，新行 475）
- 位置：const handleSend = async () => {（旧行 无，新行 560-567）
- 位置：const handleSend = async () => {（旧行 无，新行 589-590）
- 位置：const handleSend = async () => {（旧行 无，新行 621-622）

## front/src/features/ResourcePanel/index.vue（修改，+106 -10）
- 位置：顶层（旧行 无，新行 18-30）
- 位置：顶层（旧行 58，新行 71）
- 位置：const memoryUsage = ref(42);（旧行 无，新行 98-100）
- 位置：const memoryUsage = ref(42);（旧行 86-93，新行 102-103）
- 位置：const selectFile = (file: File) => {（旧行 无，新行 111-190）
- 位置：const exportLogs = () => {（旧行 110，新行 200-206）

## front/src/features/TaskSidebar/index.vue（修改，+12 -6）
- 位置：const fetchTasksFromApi = async () => {（旧行 139-142，新行 139-141）
- 位置：const fetchTasksFromApi = async () => {（旧行 159，新行 158-165）
- 位置：const filteredCompletedTasks = computed(() => {（旧行 344，新行 350）

## front/src/utils/sse.js（修改，+1 -1）
- 位置：export function getConversationStreamUrl(sessionId) {（旧行 135，新行 135）

## interaction/capabilities/capability_manager.py（修改，+6 -1）
- 位置：class CapabilityManager:（旧行 无，新行 175-179）
- 位置：class CapabilityManager:（旧行 203，新行 208）

## interaction/capabilities/llm/qwen_llm.py（修改，+10 -11）
- 位置：class QwenLLM(ILLMCapability):（旧行 29-34，新行 29-33）
- 位置：class QwenLLM(ILLMCapability):（旧行 36，新行 35）
- 位置：class QwenLLM(ILLMCapability):（旧行 41-42，新行 40-41）
- 位置：class QwenLLM(ILLMCapability):（旧行 46，新行 45）
- 位置：class QwenLLM(ILLMCapability):（旧行 259，新行 258）

## interaction/capabilities/memory/interface.py（修改，+13 -0）
- 位置：class IMemoryCapability(CapabilityBase):（旧行 无，新行 34-46）

## interaction/capabilities/memory/mem0_memory.py（修改，+131 -7）
- 位置：顶层（旧行 1-2，新行 1-2）
- 位置：from .qwen_embedding import QwenEmbedding（旧行 无，新行 8）
- 位置：class Mem0Memory(IMemoryCapability):（旧行 无，新行 20-21）
- 位置：class Mem0Memory(IMemoryCapability):（旧行 无，新行 38）
- 位置：class Mem0Memory(IMemoryCapability):（旧行 无，新行 88-111）
- 位置：class Mem0Memory(IMemoryCapability):（旧行 95-97，新行 123-131）
- 位置：class Mem0Memory(IMemoryCapability):（旧行 104-105，新行 138-229）

## interaction/capabilities/schedule_manager/common_schedule_manager.py（修改，+161 -9）
- 位置：from typing import Dict, Any, Optional（旧行 无，新行 2）
- 位置：class CommonSchedule(IScheduleManagerCapability):（旧行 无，新行 47-53）
- 位置：class CommonSchedule(IScheduleManagerCapability):（旧行 47-50，新行 55-57）
- 位置：class CommonSchedule(IScheduleManagerCapability):（旧行 52-55，新行 59-62）
- 位置：class CommonSchedule(IScheduleManagerCapability):（旧行 无，新行 67-121）
- 位置：class CommonSchedule(IScheduleManagerCapability):（旧行 无，新行 184-273）
- 位置：class CommonSchedule(IScheduleManagerCapability):（旧行 245，新行 397）

## interaction/capabilities/task_execution_manager/common_task_execution_manager.py（修改，+51 -10）
- 位置：class CommonTaskExecution(ITaskExecutionManagerCapability):（旧行 无，新行 58-60）
- 位置：class CommonTaskExecution(ITaskExecutionManagerCapability):（旧行 68，新行 71）
- 位置：class CommonTaskExecution(ITaskExecutionManagerCapability):（旧行 91-99，新行 94-140）

## interaction/capabilities/user_input_manager/common_user_input_manager.py（修改，+37 -10）
- 位置：class CommonUserInput(IUserInputManagerCapability):（旧行 无，新行 12-23）
- 位置：class CommonUserInput(IUserInputManagerCapability):（旧行 80-81，新行 92-102）
- 位置：class CommonUserInput(IUserInputManagerCapability):（旧行 101，新行 122）
- 位置：class CommonUserInput(IUserInputManagerCapability):（旧行 无，新行 137-142）
- 位置：class CommonUserInput(IUserInputManagerCapability):（旧行 120-124，新行 147-151）
- 位置：class CommonUserInput(IUserInputManagerCapability):（旧行 130-131，新行 157-158）

## interaction/common/task_draft.py（修改，+3 -1）
- 位置：class ScheduleDTO(BaseModel):（旧行 无，新行 30-31）
- 位置：class TaskDraftDTO(BaseModel):（旧行 64，新行 66）

## interaction/entry_layer/api_server.py（修改，+100 -5）
- 位置：from collections import defaultdict（旧行 9，新行 9）
- 位置：from capabilities.capbility_config import CapabilityConfig（旧行 无，新行 20-22）
- 位置：class ResumeTaskResponse(BaseModel):（旧行 无，新行 54-59）
- 位置：def trigger_memory_extraction(session_id: str, user_id: str):（旧行 无，新行 103-117）
- 位置：async def resume_task(（旧行 无，新行 230-289）
- 位置：async def get_user_sessions(user_id: str):（旧行 242-245，新行 326-340）

## interaction/external/client/task_client.py（修改，+40 -1）
- 位置：from typing import Dict, Any, Optional（旧行 无，新行 2）
- 位置：class TaskClient:（旧行 无，新行 12-13）
- 位置：class TaskClient:（旧行 无，新行 151-186）
- 位置：class TaskClient:（旧行 444，新行 483）

## interaction/external/database/dialog_state_repo.py（修改，+20 -1）
- 位置：class DialogStateRepository:（旧行 191，新行 191-210）

## interaction/interaction_handler.py（修改，+231 -104）
- 位置：顶层（旧行 1，新行 无）
- 位置：import logging（旧行 无，新行 2-4）
- 位置：from typing import Dict, Any, Optional（旧行 6-15，新行 8）
- 位置：from capabilities.system_response_manager.interface import ISystemResponseManage（旧行 无，新行 19-20）
- 位置：class InteractionHandler:（旧行 无，新行 34-71）
- 位置：class InteractionHandler:（旧行 64-139，新行 无）
- 位置：class InteractionHandler:（旧行 359，新行 316）
- 位置：class InteractionHandler:（旧行 426-428，新行 383-384）
- 位置：class InteractionHandler:（旧行 432，新行 388）
- 位置：class InteractionHandler:（旧行 520，新行 476-477）
- 位置：class InteractionHandler:（旧行 无，新行 525-536）
- 位置：class InteractionHandler:（旧行 无，新行 567-575）
- 位置：class InteractionHandler:（旧行 678，新行 656）
- 位置：class InteractionHandler:（旧行 680-684，新行 658-705）
- 位置：class InteractionHandler:（旧行 无，新行 771-865）
- 位置：class InteractionHandler:（旧行 无，新行 877-891）
- 位置：class InteractionHandler:（旧行 764-767，新行 895）
- 位置：class InteractionHandler:（旧行 805，新行 无）

## interaction/main.py（修改，+1 -1）
- 位置：if __name__ == "__main__":（旧行 37，新行 37）

## node_modules/.package-lock.json（修改，+38 -0）
- 位置：顶层（旧行 无，新行 109-125）
- 位置：顶层（旧行 无，新行 228-248）

## start_interaction.py（修改，+2 -2）
- 位置：subprocess.run([（旧行 15，新行 15）
- 位置：subprocess.run([（旧行 17，新行 17）

## start_tasks.py（修改，+2 -2）
- 位置：subprocess.run([（旧行 15，新行 15）
- 位置：subprocess.run([（旧行 19，新行 19）

## start_trigger.py（修改，+7 -5）
- 位置：print(f"工作目录: {project_root}")（旧行 11-15，新行 11-17）

## tasks/agents/agent_actor.py（修改，+76 -7）
- 位置：from common.event import EventType（旧行 无，新行 26）
- 位置：class AgentActor(Actor):（旧行 102，新行 103-107）
- 位置：class AgentActor(Actor):（旧行 无，新行 164-177）
- 位置：class AgentActor(Actor):（旧行 160，新行 179-182）
- 位置：class AgentActor(Actor):（旧行 252，新行 无）
- 位置：class AgentActor(Actor):（旧行 无，新行 306-328）
- 位置：class AgentActor(Actor):（旧行 295，新行 339）
- 位置：class AgentActor(Actor):（旧行 无，新行 341-350）
- 位置：class AgentActor(Actor):（旧行 无，新行 362-365）
- 位置：class AgentActor(Actor):（旧行 无，新行 369-370）
- 位置：class AgentActor(Actor):（旧行 无，新行 425-432）
- 位置：class AgentActor(Actor):（旧行 无，新行 445）
- 位置：class AgentActor(Actor):（旧行 412，新行 481）
- 位置：class AgentActor(Actor):（旧行 521-522，新行 590-591）

## tasks/agents/leaf_actor.py（修改，+29 -4）
- 位置：from common.event.event_type import EventType（旧行 无，新行 9）
- 位置：class LeafActor(Actor):（旧行 48，新行 49-53）
- 位置：class LeafActor(Actor):（旧行 68，新行 73-77）
- 位置：class LeafActor(Actor):（旧行 129，新行 138）
- 位置：class LeafActor(Actor):（旧行 无，新行 154-163）
- 位置：class LeafActor(Actor):（旧行 无，新行 204-209）
- 位置：class LeafActor(Actor):（旧行 312，新行 337）

## tasks/agents/tree/node_service.py（修改，+8 -2）
- 位置：class NodeService:（旧行 40，新行 40-41）
- 位置：class NodeService:（旧行 43，新行 44）
- 位置：class NodeService:（旧行 无，新行 49）
- 位置：class NodeService:（旧行 无，新行 156-159）

## tasks/agents/tree/relationship_service.py（修改，+5 -3）
- 位置：class RelationshipService:（旧行 37，新行 37-38）
- 位置：class RelationshipService:（旧行 39，新行 40）
- 位置：class RelationshipService:（旧行 无，新行 45）
- 位置：class RelationshipService:（旧行 451，新行 453）

## tasks/agents/tree/tree_manager.py（修改，+12 -4）
- 位置：from external.repositories.agent_structure_repo import AgentStructureRepository（旧行 无，新行 7）
- 位置：class TreeManager:（旧行 27，新行 28-31）
- 位置：class TreeManager:（旧行 136-138，新行 140-146）

## tasks/capabilities/__init__.py（修改，+30 -31）
- 位置：顶层（旧行 无，新行 2）
- 位置：from .capability_base import CapabilityBase（旧行 6-20，新行 7-32）
- 位置：__all__ = [（旧行 27-40，新行 39）
- 位置：_global_manager = None（旧行 44，新行 43）
- 位置：def get_capability(name: str, expected_type: type) -> CapabilityBase:（旧行 100，新行 99）

## tasks/capabilities/capability_manager.py（修改，+9 -2）
- 位置：class CapabilityManager:（旧行 18，新行 18）
- 位置：class CapabilityManager:（旧行 无，新行 20-21）
- 位置：class CapabilityManager:（旧行 无，新行 57-59）
- 位置：class CapabilityManager:（旧行 无，新行 67-68）
- 位置：class CapabilityManager:（旧行 200，新行 207）

## tasks/capabilities/capbility_config.py（修改，+4 -2）
- 位置：class CapabilityConfig:（旧行 18，新行 18）
- 位置：class CapabilityConfig:（旧行 无，新行 25-26）
- 位置：class CapabilityConfig:（旧行 86，新行 88）

## tasks/capabilities/context_resolver/tree_context_resolver.py（修改，+88 -7）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 47，新行 47）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 93，新行 93-95）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 无，新行 107-115）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 108，新行 119）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 119-121，新行 130-137）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 无，新行 168-201）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 无，新行 278-308）
- 位置：class TreeContextResolver(IContextResolverCapbility):（旧行 657，新行 738）

## tasks/capabilities/excution/connect/dify_connector.py（修改，+189 -8）
- 位置：from typing import Dict, Any, List（旧行 无，新行 2）
- 位置：class DifyConnector(BaseConnector):（旧行 无，新行 45-54）
- 位置：class DifyConnector(BaseConnector):（旧行 59，新行 70-72）
- 位置：class DifyConnector(BaseConnector):（旧行 63，新行 76-77）
- 位置：class DifyConnector(BaseConnector):（旧行 无，新行 86-186）
- 位置：class DifyConnector(BaseConnector):（旧行 无，新行 242-246）
- 位置：class DifyConnector(BaseConnector):（旧行 157，新行 277-278）
- 位置：class DifyConnector(BaseConnector):（旧行 无，新行 304-317）
- 位置：class DifyConnector(BaseConnector):（旧行 185，新行 320）
- 位置：class DifyConnector(BaseConnector):（旧行 无，新行 325-329）
- 位置：class DifyConnector(BaseConnector):（旧行 193，新行 333-334）
- 位置：class DifyConnector(BaseConnector):（旧行 无，新行 379-390）
- 位置：class DifyConnector(BaseConnector):（旧行 240，新行 393）
- 位置：class DifyConnector(BaseConnector):（旧行 246，新行 399-405）
- 位置：class DifyConnector(BaseConnector):（旧行 264，新行 423-445）

## tasks/capabilities/llm/qwen_llm.py（修改，+11 -12）
- 位置：class QwenLLM(ILLMCapability):（旧行 27-33，新行 27-32）
- 位置：class QwenLLM(ILLMCapability):（旧行 35，新行 34）
- 位置：class QwenLLM(ILLMCapability):（旧行 40-41，新行 39-40）
- 位置：class QwenLLM(ILLMCapability):（旧行 45，新行 44）
- 位置：class QwenLLM(ILLMCapability):（旧行 257，新行 256）

## tasks/capabilities/llm_memory/__init__.py（修改，+15 -4）
- 位置：顶层（旧行 3-5，新行 3-7）
- 位置：from .unified_manageer.short_term import ShortTermMemory（旧行 无，新行 10-18）
- 位置：from .unified_manageer.short_term import ShortTermMemory（旧行 9，新行 无）
- 位置：__all__ = ['UnifiedMemory', 'UnifiedMemoryManager', 'ShortTermMemory']（旧行 无，新行 21）

## tasks/capabilities/llm_memory/unified_manageer/manager.py（修改，+53 -18）
- 位置：from mem0 import Memory（旧行 12，新行 12）
- 位置：from config import MEM0_CONFIG（旧行 15，新行 15-23）
- 位置：class UnifiedMemoryManager():（旧行 35，新行 43-44）
- 位置：class UnifiedMemoryManager():（旧行 48，新行 57）
- 位置：class UnifiedMemoryManager():（旧行 60，新行 69）
- 位置：class UnifiedMemoryManager():（旧行 63-64，新行 72）
- 位置：class UnifiedMemoryManager():（旧行 77，新行 85）
- 位置：class UnifiedMemoryManager():（旧行 83，新行 91）
- 位置：class UnifiedMemoryManager():（旧行 87，新行 95）
- 位置：class UnifiedMemoryManager():（旧行 91，新行 99）
- 位置：class UnifiedMemoryManager():（旧行 无，新行 105）
- 位置：class UnifiedMemoryManager():（旧行 无，新行 116）
- 位置：class UnifiedMemoryManager():（旧行 无，新行 126）
- 位置：class UnifiedMemoryManager():（旧行 157，新行 168-171）
- 位置：class UnifiedMemoryManager():（旧行 170，新行 184-187）
- 位置：class UnifiedMemoryManager():（旧行 185，新行 202-205）
- 位置：class UnifiedMemoryManager():（旧行 无，新行 212-214）
- 位置：class UnifiedMemoryManager():（旧行 195，新行 218）
- 位置：class UnifiedMemoryManager():（旧行 205，新行 228-229）
- 位置：class UnifiedMemoryManager():（旧行 207，新行 无）
- 位置：class UnifiedMemoryManager():（旧行 无，新行 235-242）
- 位置：class UnifiedMemoryManager():（旧行 347，新行 378-382）

## tasks/capabilities/llm_memory/unified_manageer/short_term.py（修改，+9 -1）
- 位置：class ShortTermMemory:（旧行 无，新行 17-20）
- 位置：class ShortTermMemory:（旧行 无，新行 25-28）
- 位置：class ShortTermMemory:（旧行 26，新行 34）

## tasks/capabilities/llm_memory/unified_memory.py（修改，+44 -28）
- 位置：from .interface import IMemoryCapability（旧行 12，新行 12）
- 位置：class UnifiedMemory(IMemoryCapability):（旧行 无，新行 64）
- 位置：class UnifiedMemory(IMemoryCapability):（旧行 102-125，新行 103-104）
- 位置：class UnifiedMemory(IMemoryCapability):（旧行 无，新行 163-172）
- 位置：class UnifiedMemory(IMemoryCapability):（旧行 187-188，新行 176）
- 位置：class UnifiedMemory(IMemoryCapability):（旧行 无，新行 178-205）
- 位置：class UnifiedMemory(IMemoryCapability):（旧行 215，新行 231）

## tasks/capabilities/task_planning/__init__.py（修改，+15 -3）
- 位置：顶层（旧行 3-4，新行 3-6）
- 位置：from .common_task_planner import CommonTaskPlanning（旧行 无，新行 9-17）
- 位置：from .common_task_planner import CommonTaskPlanning（旧行 8，新行 19-20）

## tasks/capabilities/task_planning/common_task_planner.py（修改，+27 -3）
- 位置：class CommonTaskPlanning(ITaskPlanningCapability):（旧行 36，新行 36）
- 位置：class CommonTaskPlanning(ITaskPlanningCapability):（旧行 60，新行 60-68）
- 位置：class CommonTaskPlanning(ITaskPlanningCapability):（旧行 无，新行 100-110）
- 位置：class CommonTaskPlanning(ITaskPlanningCapability):（旧行 无，新行 117-121）
- 位置：class CommonTaskPlanning(ITaskPlanningCapability):（旧行 731，新行 755）

## tasks/capabilities/text_to_sql/utils.py（修改，+5 -5）
- 位置：import re（旧行 3，新行 3）
- 位置：def is_safe_sql(sql: str) -> bool:（旧行 13-15，新行 13-15）
- 位置：def should_learn(df, sql: str) -> bool:（旧行 39，新行 39）

## tasks/capabilities/text_to_sql/vanna/vanna_qwen_chroma.py（修改，+2 -2）
- 位置：from dashscope import Generation（旧行 9，新行 9）
- 位置：class QwenChromeVanna(ChromaDB_VectorStore, VannaBase, IVannaService):（旧行 117，新行 117）

## tasks/capabilities/text_to_sql/vanna_text_to_sql.py（修改，+29 -13）
- 位置：from .vanna.vanna_factory import VannaFactory（旧行 15，新行 15）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 无，新行 29）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 无，新行 56）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 57，新行 59-61）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 62，新行 66-68）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 124，新行 130）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 无，新行 132）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 127-128，新行 134-144）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 137，新行 153）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 139，新行 155）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 148-151，新行 164-167）
- 位置：class VannaTextToSQL(ITextToSQLCapability):（旧行 156，新行 172）

## tasks/capability_actors/execution_actor.py（修改，+74 -4）
- 位置：from capabilities.excution import BaseExecution（旧行 无，新行 17-18）
- 位置：class ExecutionActor(Actor):（旧行 34，新行 36）
- 位置：class ExecutionActor(Actor):（旧行 81-82，新行 无）
- 位置：class ExecutionActor(Actor):（旧行 无，新行 84）
- 位置：class ExecutionActor(Actor):（旧行 无，新行 86-151）
- 位置：class ExecutionActor(Actor):（旧行 227，新行 294-297）

## tasks/capability_actors/mcp_actor.py（修改，+201 -11）
- 位置：import json（旧行 4，新行 4）
- 位置：from capabilities.llm.interface import ILLMCapability（旧行 无，新行 8）
- 位置：from capabilities.llm.interface import ILLMCapability（旧行 无，新行 10-14）
- 位置：class MCPCapabilityActor(Actor):（旧行 无，新行 26-29）
- 位置：class MCPCapabilityActor(Actor):（旧行 无，新行 39-47）
- 位置：class MCPCapabilityActor(Actor):（旧行 无，新行 51-60）
- 位置：class MCPCapabilityActor(Actor):（旧行 64，新行 93）
- 位置：class MCPCapabilityActor(Actor):（旧行 79-85，新行 108-117）
- 位置：class MCPCapabilityActor(Actor):（旧行 无，新行 127-165）
- 位置：class MCPCapabilityActor(Actor):（旧行 112，新行 183）
- 位置：class MCPCapabilityActor(Actor):（旧行 119，新行 190-309）

## tasks/capability_actors/result_aggregator_actor.py（修改，+5 -5）
- 位置：class ResultAggregatorActor(Actor):（旧行 148，新行 148）
- 位置：class ResultAggregatorActor(Actor):（旧行 212，新行 212）
- 位置：class ResultAggregatorActor(Actor):（旧行 229，新行 229）
- 位置：class ResultAggregatorActor(Actor):（旧行 233，新行 233）
- 位置：class ResultAggregatorActor(Actor):（旧行 514，新行 514）

## tasks/capability_actors/task_group_aggregator_actor.py（修改，+50 -1）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 无，新行 90-91）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 无，新行 141-143）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 无，新行 178-184）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 无，新行 313）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 无，新行 370-395）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 无，新行 410-419）
- 位置：class TaskGroupAggregatorActor(Actor):（旧行 494，新行 543）

## tasks/common/messages/task_messages.py（修改，+1 -1）
- 位置：class MCPTaskRequestMessage(TaskMessage):（旧行 无，新行 85）
- 位置：class TaskCompletedMessage(TaskMessage):（旧行 137，新行 无）

## tasks/common/taskspec/task_spec.py（修改，+1 -1）
- 位置：class TaskSpec(BaseModel):（旧行 无，新行 142）
- 位置：class TaskSpec(BaseModel):（旧行 149，新行 无）

## tasks/entry_layer/api_server.py（修改，+129 -13）
- 位置：from pydantic import BaseModel（旧行 14，新行 无）
- 位置：from common.messages.task_messages import AgentTaskMessage, ResumeTaskMessage（旧行 20，新行 19-20）
- 位置：app.add_middleware(（旧行 42-43，新行 42-45）
- 位置：actor_system = ActorSystem('simpleSystemBase')（旧行 45-46，新行 47-85）
- 位置：class TaskRequest(BaseModel):（旧行 无，新行 91-93）
- 位置：class ResumeRequest(BaseModel):（旧行 无，新行 99-148）
- 位置：def execute_task(req: TaskRequest):（旧行 无，新行 163-164）
- 位置：def execute_task(req: TaskRequest):（旧行 无，新行 169-178）
- 位置：def execute_task(req: TaskRequest):（旧行 76-78，新行 180-187）
- 位置：def execute_task(req: TaskRequest):（旧行 83，新行 192）
- 位置：def resume_task(req: ResumeRequest):（旧行 无，新行 227-228）
- 位置：def resume_task(req: ResumeRequest):（旧行 无，新行 230-232）
- 位置：def resume_task(req: ResumeRequest):（旧行 122，新行 236-238）
- 位置：def resume_task(req: ResumeRequest):（旧行 126，新行 242）
- 位置：if __name__ == '__main__':（旧行 247，新行 363）

## tasks/events/event_bus.py（修改，+47 -1）
- 位置：import uuid（旧行 无，新行 9-10）
- 位置：class EventPublisher:（旧行 222，新行 224-268）

## tasks/external/__init__.py（修改，+17 -22）
- 位置：顶层（旧行 3-8，新行 3-9）
- 位置：from . import repositories（旧行 10，新行 无）
- 位置：from . import repositories（旧行 12-26，新行 12-21）

## tasks/external/database/connection_pool.py（修改，+6 -6）
- 位置：class MySQLConnectionPool(BaseConnectionPool):（旧行 79，新行 79）
- 位置：class PostgreSQLConnectionPool(BaseConnectionPool):（旧行 168，新行 168）
- 位置：class SQLServerConnectionPool(BaseConnectionPool):（旧行 252，新行 252）
- 位置：class OracleConnectionPool(BaseConnectionPool):（旧行 349，新行 349）
- 位置：class ConnectionPoolFactory:（旧行 418，新行 418）
- 位置：class ConnectionPoolFactory:（旧行 440，新行 440）

## tasks/external/database/neo4j_client.py（修改，+1 -1）
- 位置：from typing import Any, List, Dict, Optional（旧行 4，新行 4）

## tasks/external/database/redis_client.py（修改，+1 -1）
- 位置：from typing import Any, Optional（旧行 4，新行 4）

## tasks/external/memory_store/__init__.py（修改，+26 -22）
- 位置：顶层（旧行 1-9，新行 1-13）
- 位置：from .memory_repos import build_vault_repo, build_procedural_repo, build_resourc（旧行 11-23，新行 15-27）

## tasks/external/memory_store/filebased_procedural_repository.py（修改，+44 -12）
- 位置：from typing import List, Optional, TYPE_CHECKING（旧行 无，新行 3）
- 位置：import numpy as np（旧行 10，新行 无）
- 位置：class FileBasedProceduralRepository:（旧行 16-19，新行 16-24）
- 位置：class FileBasedProceduralRepository:（旧行 35，新行 40）
- 位置：class FileBasedProceduralRepository:（旧行 61，新行 66-91）
- 位置：class FileBasedProceduralRepository:（旧行 64，新行 94）
- 位置：class FileBasedProceduralRepository:（旧行 70-71，新行 100-103）
- 位置：class FileBasedProceduralRepository:（旧行 83-84，新行 115-116）

## tasks/external/memory_store/memory_repos.py（修改，+18 -12）
- 位置：顶层（旧行 2-11，新行 2-7）
- 位置：def build_vault_repo() -> IVaultRepository:（旧行 无，新行 13-16）
- 位置：def build_procedural_repo() -> IProceduralRepository:（旧行 无，新行 23-24）
- 位置：def build_resource_repo() -> IResourceRepository:（旧行 无，新行 29-32）
- 位置：def build_resource_repo() -> IResourceRepository:（旧行 33-34，新行 39-40）

## tasks/external/memory_store/stm_dao.py（修改，+17 -1）
- 位置：class STMRecordDAO:（旧行 无，新行 50-65）
- 位置：class STMRecordDAO:（旧行 57，新行 73）

## tasks/main.py（修改，+7 -1）
- 位置：import sys（旧行 无，新行 11-16）
- 位置：def main():（旧行 143，新行 149）

## trigger/main.py（修改，+1 -1）
- 位置：if __name__ == "__main__":（旧行 131，新行 131）

## trigger/config/settings.py（修改，+4 -4）

### 行 47：默认 rabbitmq_url 修改
```python
# 旧代码
"rabbitmq_url": "amqp://guest:guest@localhost:5672/",

# 新代码
"rabbitmq_url": "amqp://admin:Lanba%40123@121.36.203.36:10005/prod",
```

### 行 79：EVENTS_SERVICE_BASE_URL 默认值修改
```python
# 旧代码
self.EVENTS_SERVICE_BASE_URL = os.getenv("EVENTS_SERVICE_BASE_URL", self._config_data.get("events_service_base_url", "http://localhost:8004"))

# 新代码
self.EVENTS_SERVICE_BASE_URL = os.getenv("EVENTS_SERVICE_BASE_URL", self._config_data.get("events_service_base_url", "http://localhost:8000"))
```

### 行 86：EXTERNAL_SYSTEM_URL 默认值修改
```python
# 旧代码
self.EXTERNAL_SYSTEM_URL = os.getenv("EXTERNAL_SYSTEM_URL", self._config_data.get("external_system_url", "http://localhost:8004"))

# 新代码
self.EXTERNAL_SYSTEM_URL = os.getenv("EXTERNAL_SYSTEM_URL", self._config_data.get("external_system_url", "http://localhost:8000"))
```

## trigger/services/schedule_scanner.py（修改，+41 -12）

### 行 1-8：import 修改
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

### 行 12-23：新增函数 get_root_agent_id()
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

### 行 68-98：_scan_pending_tasks() 消息构建逻辑重构
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

## tasks/external/message_queue/rabbitmq_listener.py（修改，+75 -30）

### 行 5：新增 import
```python
# 新增
from urllib.parse import urlparse
```

### 行 40-48：__init__() 修改
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

### 行 50-67：新增方法 _parse_rabbitmq_url()
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

### 行 71-127：callback() 方法重构

#### START_TASK 处理逻辑
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

#### RESUME_TASK 处理逻辑
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

### 行 129-167：start() 方法重构
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

## 未跟踪文件（不在 main 中）
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
- dify_workflow/catalog.yml
- dify_workflow/dify.png
- dify_workflow/marketing_graph.cypher
- dify_workflow/records (1).json
- "dify_workflow/\350\220\245\351\224\200.xmind"
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
