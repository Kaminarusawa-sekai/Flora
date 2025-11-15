"""上下文解析器实现"""
from typing import Dict, Any, List, Optional, Tuple
from ..capability_base import CapabilityBase
import logging
import json
import re


class ContextResolver(CapabilityBase):
    """
    上下文解析器
    负责从请求中提取上下文信息，支持模板化和变量替换
    从TaskCoordinator._extract_context迁移而来
    """
    
    def __init__(self):
        """
        初始化上下文解析器
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.context_templates = {}
        self.variable_pattern = re.compile(r'\$\{([^}]+)\}')
        self.data_providers = {}
        self.registry = None
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'context_resolution'
    
    def extract_context(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从TaskCoordinator._extract_context迁移
        从任务数据中提取上下文信息
        
        Args:
            task_data: 任务原始数据
            
        Returns:
            Dict[str, Any]: 提取的上下文信息
        """
        try:
            # 1. 基础上下文提取
            base_context = self._extract_base_context(task_data)
            
            # 2. 任务类型特定上下文
            task_type = base_context.get('task_type')
            if task_type:
                task_specific = self._extract_task_specific_context(task_data, task_type)
                base_context.update(task_specific)
            
            # 3. 应用模板（如果有）
            template_name = base_context.get('context_template')
            if template_name:
                base_context = self._apply_context_template(base_context, template_name)
            
            # 4. 变量替换
            resolved_context = self._resolve_variables(base_context, task_data)
            
            # 5. 清理和验证
            cleaned_context = self._clean_and_validate_context(resolved_context)
            
            return cleaned_context
            
        except Exception as e:
            self.logger.error(f"Error extracting context: {str(e)}", exc_info=True)
            # 返回基础错误上下文
            return {
                'task_id': task_data.get('task_id', 'unknown'),
                'error': str(e),
                'original_data': task_data,
                'extraction_failed': True
            }
    
    def _extract_base_context(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取基础上下文信息
        
        Args:
            task_data: 任务原始数据
            
        Returns:
            Dict[str, Any]: 基础上下文
        """
        base_context = {}
        
        # 提取常见字段
        common_fields = ['task_id', 'task_type', 'priority', 'timestamp', 
                        'source', 'target', 'user_id', 'session_id']
        
        for field in common_fields:
            if field in task_data:
                base_context[field] = task_data[field]
        
        # 提取内容字段
        content_fields = ['content', 'query', 'message', 'text', 'prompt']
        for field in content_fields:
            if field in task_data:
                base_context['content'] = task_data[field]
                break
        
        # 提取参数字段
        if 'params' in task_data:
            base_context['params'] = task_data['params']
        elif 'parameters' in task_data:
            base_context['params'] = task_data['parameters']
        
        # 提取元数据
        if 'metadata' in task_data:
            base_context['metadata'] = task_data['metadata']
        
        # 提取依赖关系
        if 'depends_on' in task_data:
            base_context['depends_on'] = task_data['depends_on']
        
        return base_context
    
    def _extract_task_specific_context(self, task_data: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """
        提取任务类型特定的上下文
        
        Args:
            task_data: 任务原始数据
            task_type: 任务类型
            
        Returns:
            Dict[str, Any]: 任务特定上下文
        """
        specific_context = {}
        
        # 根据任务类型提取特定字段
        if task_type == 'data_query':
            # 数据查询任务
            specific_context['query_type'] = task_data.get('query_type', 'sql')
            specific_context['data_source'] = task_data.get('data_source', 'default')
            specific_context['filters'] = task_data.get('filters', {})
            specific_context['sort_by'] = task_data.get('sort_by', [])
            
        elif task_type == 'llm_generation':
            # LLM生成任务
            specific_context['model'] = task_data.get('model', 'default')
            specific_context['temperature'] = task_data.get('temperature', 0.7)
            specific_context['max_tokens'] = task_data.get('max_tokens', 1000)
            specific_context['system_prompt'] = task_data.get('system_prompt', '')
            specific_context['messages'] = task_data.get('messages', [])
            
        elif task_type == 'analysis':
            # 分析任务
            specific_context['analysis_type'] = task_data.get('analysis_type', 'general')
            specific_context['data'] = task_data.get('data', {})
            specific_context['metrics'] = task_data.get('metrics', [])
            
        elif task_type == 'decision_making':
            # 决策任务
            specific_context['decision_options'] = task_data.get('options', [])
            specific_context['criteria'] = task_data.get('criteria', {})
            specific_context['constraints'] = task_data.get('constraints', [])
            
        # 其他任务类型的特定字段可以在这里添加
        
        return specific_context
    
    def _apply_context_template(self, context: Dict[str, Any], template_name: str) -> Dict[str, Any]:
        """
        应用上下文模板
        
        Args:
            context: 当前上下文
            template_name: 模板名称
            
        Returns:
            Dict[str, Any]: 应用模板后的上下文
        """
        template = self.context_templates.get(template_name)
        if not template:
            self.logger.warning(f"Template not found: {template_name}")
            return context
        
        # 创建模板的深拷贝以避免修改原始模板
        from copy import deepcopy
        applied_context = deepcopy(template)
        
        # 用当前上下文的值覆盖模板中的值
        for key, value in context.items():
            applied_context[key] = value
        
        return applied_context
    
    def _resolve_variables(self, context: Dict[str, Any], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析上下文中的变量引用
        
        Args:
            context: 当前上下文
            task_data: 原始任务数据
            
        Returns:
            Dict[str, Any]: 解析变量后的上下文
        """
        # 创建变量源
        variable_sources = {
            'context': context,
            'task_data': task_data,
            'env': {}
        }
        
        # 解析字典中的所有字符串值
        return self._recursive_resolve(context, variable_sources)
    
    def _recursive_resolve(self, obj: Any, sources: Dict[str, Any]) -> Any:
        """
        递归解析对象中的变量
        
        Args:
            obj: 要解析的对象
            sources: 变量源
            
        Returns:
            Any: 解析后的对象
        """
        if isinstance(obj, str):
            # 解析字符串中的变量
            return self._resolve_string_variables(obj, sources)
        elif isinstance(obj, dict):
            # 递归解析字典
            result = {}
            for key, value in obj.items():
                result[key] = self._recursive_resolve(value, sources)
            return result
        elif isinstance(obj, list):
            # 递归解析列表
            return [self._recursive_resolve(item, sources) for item in obj]
        else:
            # 其他类型保持不变
            return obj
    
    def _resolve_string_variables(self, text: str, sources: Dict[str, Any]) -> str:
        """
        解析字符串中的变量引用
        支持 ${source.key.path} 格式
        
        Args:
            text: 包含变量引用的文本
            sources: 变量源字典
            
        Returns:
            str: 解析后的文本
        """
        def replace_var(match):
            var_path = match.group(1)
            
            # 解析变量路径，格式为 source.key1.key2...
            parts = var_path.split('.')
            if not parts:
                return match.group(0)  # 返回原始内容
            
            # 获取变量源
            source_name = parts[0]
            source = sources.get(source_name)
            if source is None:
                self.logger.warning(f"Variable source not found: {source_name}")
                return match.group(0)
            
            # 获取变量值
            value = source
            for part in parts[1:]:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    self.logger.warning(f"Variable path not found: {var_path}")
                    return match.group(0)
            
            # 如果值是可调用的，调用它
            if callable(value):
                try:
                    value = value()
                except Exception as e:
                    self.logger.error(f"Error calling variable {var_path}: {str(e)}")
                    return match.group(0)
            
            return str(value)
        
        # 替换所有变量
        resolved_text = self.variable_pattern.sub(replace_var, text)
        return resolved_text
    
    def _clean_and_validate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理和验证上下文
        
        Args:
            context: 上下文
            
        Returns:
            Dict[str, Any]: 清理后的上下文
        """
        # 移除None值
        cleaned = {k: v for k, v in context.items() if v is not None}
        
        # 验证必要字段
        if 'task_type' not in cleaned:
            self.logger.warning("Context missing task_type, defaulting to 'general'")
            cleaned['task_type'] = 'general'
        
        # 设置默认值
        if 'priority' not in cleaned:
            cleaned['priority'] = 'medium'
        
        # 限制上下文大小，避免过大的上下文
        self._limit_context_size(cleaned)
        
        return cleaned
    
    def _limit_context_size(self, context: Dict[str, Any], max_size: int = 1024 * 1024) -> None:
        """
        限制上下文大小
        
        Args:
            context: 上下文
            max_size: 最大大小（字节）
        """
        # 计算当前大小
        context_str = json.dumps(context)
        context_size = len(context_str.encode('utf-8'))
        
        # 如果超过限制，移除大字段
        if context_size > max_size:
            # 找出最大的字段
            large_fields = sorted(
                [(k, json.dumps(v)) for k, v in context.items()],
                key=lambda x: len(x[1].encode('utf-8')),
                reverse=True
            )
            
            # 移除或截断大字段
            for field, content in large_fields:
                if field not in ['task_id', 'task_type', 'priority']:  # 保留关键字段
                    if isinstance(context[field], str):
                        # 截断字符串
                        max_length = max_size // 10  # 限制为最大大小的1/10
                        if len(context[field]) > max_length:
                            context[field] = context[field][:max_length] + '...(truncated)'
                    else:
                        # 移除非字符串大字段
                        context[field] = f'<{type(context[field]).__name__} removed due to size>'
                
                # 检查是否已经减小到限制以下
                new_size = len(json.dumps(context).encode('utf-8'))
                if new_size <= max_size:
                    break
    
    def register_context_template(self, template_name: str, template: Dict[str, Any]) -> bool:
        """
        注册上下文模板
        
        Args:
            template_name: 模板名称
            template: 模板内容
            
        Returns:
            bool: 是否注册成功
        """
        if not isinstance(template, dict):
            self.logger.error(f"Template must be a dictionary")
            return False
        
        self.context_templates[template_name] = template
        self.logger.info(f"Registered context template: {template_name}")
        return True
    
    def register_data_provider(self, provider_name: str, provider_func) -> bool:
        """
        注册数据提供者
        
        Args:
            provider_name: 提供者名称
            provider_func: 提供数据的函数
            
        Returns:
            bool: 是否注册成功
        """
        if not callable(provider_func):
            self.logger.error(f"Data provider must be callable")
            return False
        
        self.data_providers[provider_name] = provider_func
        self.logger.info(f"Registered data provider: {provider_name}")
        return True
    
    def get_context_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有上下文模板
        
        Returns:
            Dict[str, Dict[str, Any]]: 模板映射
        """
        return self.context_templates.copy()
    
    def get_data_providers(self) -> Dict[str, Any]:
        """
        获取所有数据提供者
        
        Returns:
            Dict[str, Any]: 数据提供者映射
        """
        return self.data_providers.copy()
    
    def enrich_context(self, context: Dict[str, Any], data_sources: List[str]) -> Dict[str, Any]:
        """
        丰富上下文信息
        
        Args:
            context: 基础上下文
            data_sources: 要使用的数据源列表
            
        Returns:
            Dict[str, Any]: 丰富后的上下文
        """
        enriched_context = context.copy()
        
        for source_name in data_sources:
            if source_name in self.data_providers:
                try:
                    # 调用数据提供者获取数据
                    provider_data = self.data_providers[source_name](context)
                    # 将提供者数据添加到上下文中
                    if isinstance(provider_data, dict):
                        enriched_context[f'_{source_name}_data'] = provider_data
                        # 也将顶层字段合并到上下文中（如果没有冲突）
                        for key, value in provider_data.items():
                            if key not in enriched_context:
                                enriched_context[key] = value
                except Exception as e:
                    self.logger.error(f"Error enriching context with {source_name}: {str(e)}")
        
        return enriched_context
    
    def resolve_context(self, context: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """
        解析上下文
        
        Args:
            context: 原始上下文
            agent_id: 当前Agent ID
            
        Returns:
            Dict[str, Any]: 解析后的上下文
        """
        resolved_context = context.copy()
        
        # 解析上下文中的变量
        for key, value in resolved_context.items():
            if isinstance(value, str) and value.startswith('$'):
                # 解析变量引用
                resolved_value = self._resolve_kv_via_layered_search(value[1:], agent_id, resolved_context)
                resolved_context[key] = resolved_value
        
        return resolved_context
    
    def _resolve_kv_via_layered_search(self, key: str, agent_id: str, context: Dict[str, Any]) -> Any:
        """
        通过分层搜索解析键值对
        
        Args:
            key: 要解析的键
            agent_id: 当前Agent ID
            context: 当前上下文
            
        Returns:
            Any: 解析后的值
        """
        try:
            # 1. 首先在当前上下文中查找
            if key in context:
                return context[key]
            
            # 2. 然后在Agent注册表中查找
            if self.registry and agent_id:
                agent_meta = self.registry.get_agent_meta(agent_id)
                if agent_meta and key in agent_meta:
                    return agent_meta[key]
            
            # 3. 最后查找系统级上下文
            # TODO: 实现系统级上下文查找逻辑
            
            # 如果都找不到，返回原始键
            return f'${key}'
        except Exception as e:
            self.logger.error(f"Error resolving key {key}: {str(e)}", exc_info=True)
            return f'${key}'
    
    def initialize(self, registry: Any):
        """
        初始化上下文解析器
        
        Args:
            registry: Agent注册表实例
        """
        self.registry = registry
        self.logger.info("ContextResolver initialized")