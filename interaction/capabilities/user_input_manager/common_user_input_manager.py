from typing import Dict, Any, Optional
from .interface import IUserInputManagerCapability
from common import UserInputDTO,DialogTurn
from capabilities.registry import capability_registry
from capabilities.llm.interface import ILLMCapability
from capabilities.memory.interface import IMemoryCapability
import logging
logger = logging.getLogger(__name__)

class CommonUserInput(IUserInputManagerCapability):
    """用户输入管理器 - 接收并解析用户的原始输入"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化用户输入管理器"""
        logger.info("=== 开始初始化用户输入管理器 ===")
        logger.debug(f"获取到配置信息: {list(config.keys())}")
        
        self.config = config
        
        # 初始化懒加载属性
        logger.debug("初始化LLM引用为None")
        self._llm = None
        
        logger.debug("初始化内存服务引用为None")
        self._memory = None
        
        logger.debug("初始化对话历史存储引用为None")
        self._history_store = None
        
        # 上下文窗口大小
        self.context_window = config.get("context_window", 5)
        logger.info(f"设置上下文窗口大小: {self.context_window}")
        
        logger.info("=== 用户输入管理器初始化完成 ===")
        
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            logger.info("开始懒加载LLM能力")
            self._llm = capability_registry.get_capability("llm", ILLMCapability)
            logger.info("LLM能力懒加载完成")
        return self._llm
        
    @property
    def memory(self):
        """懒加载内存服务"""
        if self._memory is None:
            logger.info("开始懒加载内存服务")
            self._memory = capability_registry.get_capability("memory", IMemoryCapability)
            logger.info("内存服务懒加载完成")
        return self._memory
        
    @property
    def history_store(self):
        """懒加载对话历史存储"""
        from capabilities.context_manager.interface import IContextManagerCapability
        if self._history_store is None:
            logger.info("开始懒加载对话历史存储")
            self._history_store = capability_registry.get_capability("context_manager", IContextManagerCapability)
            logger.info("对话历史存储懒加载完成")
        return self._history_store
    
    def shutdown(self) -> None:
        """关闭用户输入管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "input_processing"
    
    def process_input(self, user_input: UserInputDTO) -> Dict[str, Any]:
        """处理用户输入
        
        Args:
            user_input: 用户输入DTO
            
        Returns:
            处理后的输入数据，包含会话信息
        """
        logger.info("=== 开始处理用户输入 ===")
        logger.debug(f"用户输入信息: session_id={user_input.session_id}, user_id={user_input.user_id}, utterance={user_input.utterance[:50]}...")
        
        try:
            # 1. 读取会话历史
            logger.debug("步骤1: 读取会话历史")
            # 注意：我们的上下文管理器get_turns_by_session方法返回的是DialogTurn对象列表
            # 我们需要转换为方案中期望的格式
            recent_turns = self.history_store.get_turns_by_session(session_id=user_input.session_id, limit=self.context_window)
            logger.debug(f"获取到 {len(recent_turns)} 条会话历史记录")
            
            dialog_history = [
                {"role": turn.role, "utterance": turn.utterance}
                for turn in  reversed(recent_turns)
            ]
            logger.debug(f"转换后的对话历史: {dialog_history}")
            
            # 2. 检索长期记忆
            logger.debug("步骤2: 检索长期记忆")
            memories = self.memory.search_memories(
                user_id=user_input.user_id,
                query=user_input.utterance,
                limit=3
            )
            logger.info(f"检索到 {len(memories) if hasattr(memories, '__len__') else 0} 条长期记忆")
            logger.debug(f"长期记忆内容: {memories}")
            
            # 3. 构造LLM Prompt
            logger.debug("步骤3: 构造LLM Prompt")
            prompt = f"""【对话历史】
{"\n".join([f"{turn['role']}：{turn['utterance']}" for turn in dialog_history])}

【长期记忆】
{memories}

【当前输入】
{user_input.utterance}

请输出 JSON：
{{
"enhanced_utterance": "",
"resolved_references": {{}},
"implied_action": "",
"target_entity": "",
"new_time": ""
}}"""
            logger.debug(f"构造的LLM Prompt: {prompt[:200]}...")
            
            # 4. 调用LLM，解析结果
            logger.debug("步骤4: 调用LLM生成结果")
            llm_result = self.llm.generate(prompt, parse_json=True)
            logger.debug(f"LLM返回结果: {llm_result}")
            parsed_result = llm_result
            
            # 5. 构造返回数据
            logger.debug("步骤5: 构造返回数据")
            enriched_input = {
                "session_id": user_input.session_id,
                "user_id": user_input.user_id,
                "utterance": user_input.utterance,
                "enhanced_utterance": parsed_result["enhanced_utterance"],
                "resolved_references": parsed_result["resolved_references"],
                "implied_action": parsed_result["implied_action"],
                "target_entity": parsed_result["target_entity"],
                "new_time": parsed_result["new_time"],
                "dialog_history": dialog_history,
                "long_term_memories": memories,
                "timestamp": user_input.timestamp,
                "metadata": user_input.metadata
            }
            logger.debug(f"构造的增强输入数据: {enriched_input}")
            
            # 6. 保存当前输入到对话历史
            logger.debug("步骤6: 保存当前输入到对话历史")
            self.history_store.add_turn(DialogTurn(
                role="user", 
                utterance=user_input.utterance, 
                enhanced_utterance=parsed_result["enhanced_utterance"], 
                session_id=user_input.session_id, 
                user_id=user_input.user_id
            ))
            logger.info(f"已保存当前输入到对话历史，session_id={user_input.session_id}")
            
            logger.info("=== 用户输入处理完成 ===")
            return enriched_input
        except Exception as e:
            logger.exception(f"处理用户输入时发生错误: {e}")
            # 构造默认返回数据
            logger.debug("使用默认值构造返回数据")
            enriched_input = {
                "session_id": user_input.session_id,
                "user_id": user_input.user_id,
                "utterance": user_input.utterance,
                "enhanced_utterance": user_input.utterance,
                "resolved_references": {},
                "implied_action": "",
                "target_entity": "",
                "new_time": "",
                "dialog_history": [],
                "long_term_memories": [],
                "timestamp": user_input.timestamp,
                "metadata": user_input.metadata
            }
            return enriched_input