from typing import Dict, Any, Optional, List, Type, Tuple
from abc import ABC, abstractmethod

import logging

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """
    连接器抽象基类，定义连接器的公共接口

     提供统一的参数补全机制：
    1. pre_fill_known_params_with_llm() - 从 context 提取已有值
    2. enhance_param_descriptions_with_context() - 增强描述
    3. resolve_semantic_pointers() - 语义指针补全（消解歧义）
    4. resolve_context() - text_to_sql 查询
    """
    
    def __init__(self):
        """初始化连接器"""
        pass
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行连接器操作
        
        Args:
            inputs: 输入参数
            params: 配置参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        pass
    
     # ==================== 统一参数补全逻辑 ====================

    def _resolve_all_params(
        self,
        missing_params: Dict[str, str],
        context: Dict[str, Any],
        agent_id: str,
        user_id: str
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        统一的参数补全流程

        四步补全：
        1. pre_fill_known_params_with_llm() - 从 context 提取已有值
        2. enhance_param_descriptions_with_context() - 增强描述
        3. resolve_semantic_pointers() - 语义指针补全（消解歧义）
        4. resolve_context() - text_to_sql 查询

        Args:
            missing_params: 缺失参数 {param_name: description}
            context: 上下文信息，包含：
                - global_context: 全局上下文
                - enriched_context: 富上下文
                - content: 任务内容
                - description: 任务描述
            agent_id: 当前 Agent ID
            user_id: 用户 ID

        Returns:
            (filled_params, still_missing_params)
        """
        if not missing_params:
            return {}, {}

        try:
            from ...context_resolver.interface import IContextResolverCapbility
            from ... import get_capability
            context_resolver: IContextResolverCapbility = get_capability(
                "context_resolver", IContextResolverCapbility
            )
        except Exception as e:
            logger.warning(f"Failed to get context_resolver: {e}")
            return {}, missing_params

        # Step 1: 从 context 中直接提取已有值
        filled_params, remaining_params = context_resolver.pre_fill_known_params_with_llm(
            base_param_descriptions=missing_params,
            current_context_str=context
        )
        logger.info(f"Step 1 - Pre-filled: {list(filled_params.keys())}, Remaining: {list(remaining_params.keys())}")

        if not remaining_params:
            return filled_params, {}

        # 判断是否全是 ID 类型参数（用于决定上下文增强策略）
        all_id_params = all(
            self._is_id_like_param(name, desc)
            for name, desc in remaining_params.items()
        )

        # 构建用于增强的上下文
        context_for_enhance = context
        if all_id_params:
            # ID 类型参数只使用关键字段，避免噪音
            safe_context = {}
            for key in ("user_id", "tenant_id", "userid", "session_id"):
                value = (
                    context.get("global_context", {}).get(key) or
                    context.get("enriched_context", {}).get(key) or
                    context.get(key)
                )
                if value:
                    safe_context[key] = value
            context_for_enhance = safe_context or {"user_id": user_id}

        # Step 2: 用 context 增强剩余参数的描述
        enhanced_descs = context_resolver.enhance_param_descriptions_with_context(
            base_param_descriptions=remaining_params,
            current_inputs=context_for_enhance
        )
        logger.info(f"Step 2 - Enhanced descriptions: {enhanced_descs}")

        # Step 3: 语义指针补全（消解歧义）
        semantic_pointers = context_resolver.resolve_semantic_pointers(
            param_descriptions=enhanced_descs,
            current_context=context,
            agent_id=agent_id,
            user_id=user_id
        )
        final_descs = self._apply_semantic_pointers(enhanced_descs, semantic_pointers)
        logger.info(f"Step 3 - After semantic pointers: {final_descs}")

        # Step 4: 使用精确描述查询数据库
        resolved_params = context_resolver.resolve_context(final_descs, agent_id)
        logger.info(f"Step 4 - Resolved from DB: {resolved_params}")

        filled_params.update(resolved_params)

        # 检查仍然缺失的参数
        still_missing = {}
        for name, desc in remaining_params.items():
            value = filled_params.get(name)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                still_missing[name] = desc

        return filled_params, still_missing

    def _apply_semantic_pointers(
        self,
        descriptions: Dict[str, str],
        semantic_pointers: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        将语义指针应用到参数描述

        Args:
            descriptions: 原始描述 {param_name: description}
            semantic_pointers: 语义指针 {param_name: {resolved_desc, confidence, ...}}

        Returns:
            应用语义指针后的描述
        """
        result = {}
        for param_name, desc in descriptions.items():
            pointer = semantic_pointers.get(param_name)
            if pointer and isinstance(pointer, dict):
                confidence = pointer.get("confidence", 0)
                if confidence >= 0.5:  # 只使用置信度较高的语义指针
                    resolved_desc = pointer.get("resolved_desc", desc)
                    result[param_name] = resolved_desc
                    logger.info(
                        f"[SemanticPointer] '{param_name}': '{desc}' -> '{resolved_desc}' "
                        f"(confidence: {confidence:.2f})"
                    )
                else:
                    result[param_name] = desc
            else:
                result[param_name] = desc
        return result

    @staticmethod
    def _is_id_like_param(name: str, label: str = "") -> bool:
        """
        判断参数是否是 ID 类型

        Args:
            name: 参数名
            label: 参数标签/描述

        Returns:
            是否为 ID 类型参数
        """
        if name:
            name_lower = name.lower()
            if name_lower.endswith("_id") or name_lower.endswith("id"):
                return True
            if name_lower == "id":
                return True
        if label:
            label_upper = label.upper()
            if "ID" in label_upper:
                return True
        return False

    def _get_known_params(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取已知参数（扩展点）

        后续可接入全局参数表，快速获取固定参数

        Args:
            context: 上下文信息

        Returns:
            已知参数字典
        """
        known = {}
        global_ctx = context.get("global_context", {})
        enriched_ctx = context.get("enriched_context", {})

        # 常见的全局参数
        for key in ("tenant_id", "user_id", "session_id", "trace_id"):
            if key in global_ctx and global_ctx[key]:
                known[key] = global_ctx[key]
            elif key in enriched_ctx and enriched_ctx[key]:
                known[key] = enriched_ctx[key]

        return known

    # ==================== 原有接口 ====================


    def _check_missing_inputs(self, inputs: Dict[str, Any]) -> List[str]:
        """
        检查缺失的输入参数
        
        Args:
            inputs: 输入参数字典
            
        Returns:
            List[str]: 缺失的输入参数列表
        """
        return None
    
    def _get_required_params(self, params: Dict[str, Any]) -> List[str]:
        """
        获取必需配置参数列表
        
        Returns:
            List[str]: 必需配置参数列表
        """
        return []
    
    def _get_required_inputs(self) -> List[str]:
        """
        获取必需输入参数列表
        
        Returns:
            List[str]: 必需输入参数列表
        """
        return []
    
    def authenticate(self, params: Dict[str, Any]) -> bool:
        """
        执行鉴权操作
        
        Args:
            params: 配置参数
            
        Returns:
            bool: 鉴权是否成功
        """
        return True
    
    def health_check(self, params: Dict[str, Any]) -> bool:
        """
        执行健康检查
        
        Args:
            params: 配置参数
            
        Returns:
            bool: 健康检查是否通过
        """
        return True
