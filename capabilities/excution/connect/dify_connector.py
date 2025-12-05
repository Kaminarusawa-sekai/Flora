from typing import Dict, Any, List
import requests
from external.clients import DifyClient
from .base_connector import BaseConnector

import logging
logger = logging.getLogger(__name__)

class DifyConnector(BaseConnector):
    """
    Dify连接器实现
    """
    
    def __init__(self, base_url: str = None, api_key: str = None, **kwargs):
        """
        初始化连接器，存储静态配置
        
        Args:
            base_url: Dify 的 API 地址 (通常来自 config.json)
            api_key: 默认 API Key (可选，通常为空，等待运行时传入)
        """
        super().__init__()
        self.static_config = {
            "base_url": base_url,
            "api_key": api_key,
            **kwargs
        }


    def _resolve_param(self, key: str, runtime_params: Dict[str, Any]) -> Any:
        """
        解析参数：优先使用运行时参数，否则使用静态配置
        """
        # 1. 尝试从 runtime params 获取
        val = runtime_params.get(key)
        if val is not None and val != "":
            self.static_config[key] = val
            return val
            
        # 2. 尝试从 static config 获取
        val = self.static_config.get(key)
        if val is not None and val != "":
            return val
            
        return None
    def _check_missing_config_params(self, params: Dict[str, Any]) -> List[str]:
        """
        检查缺失的配置参数 (合并后检查)
        """
        required_params = ["api_key", "base_url"]
        missing = []
        for param in required_params:
            # 使用 _resolve_param 检查最终是否有值
            val = self._resolve_param(param, params)
            if not val:
                missing.append(param)
        return missing
    
    def _check_missing_inputs(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """
        检查Dify连接器缺失的输入参数（仅检查 required=True 的字段）
        """
        required_inputs = self._get_required_inputs()  # 现在返回 {var: meta}
        missing = {}
        for var_name, meta in required_inputs.items():
            if meta.get("required", False):
                value = inputs.get(var_name)
                # 判断是否为空：None、空字符串都算缺失
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing[var_name] = meta.get("label", var_name)
        return missing
    
    def _get_required_params(self) -> List[str]:
        """
        获取Dify必需配置参数列表
        """
        return ["api_key", "base_url"]
    

    def _get_required_inputs(self, params: Dict[str, Any]=None) -> Dict[str, Any]:
        """
        获取 Dify Schema
        """
        if params is None:
            params = {}
        
        api_key = self._resolve_param("api_key", params)
        base_url = self._resolve_param("base_url", params)
        if not all([api_key, base_url]):
            raise Exception("Missing required parameters for Dify schema fetch")
        
        try:
            # 调用Dify API获取Schema（这里简化处理，实际应该根据具体情况调整）
            # 注意：这里不再使用workflow_id参数
            url = f"{base_url}/parameters"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            schema = response.json()

            # === 新增：处理返回值，提取 user_input_form 字段 ===
            user_input_form = schema.get("user_input_form", [])
            required_inputs = {}

            for item in user_input_form:
                # 每个 item 是一个 dict，如 {'text-input': {...}} 或 {'paragraph': {...}}
                field_type, field_meta = next(iter(item.items()))  # 取第一个也是唯一的键值对
                variable = field_meta.get("variable")
                if variable:
                    required_inputs[variable] = {
                        "label": field_meta.get("label"),
                        "type": field_type,
                        "required": field_meta.get("required", False),
                        "max_length": field_meta.get("max_length"),
                        "options": field_meta.get("options", []),
                        "default": field_meta.get("default", ""),
                        "placeholder": field_meta.get("placeholder", ""),
                        "hint": field_meta.get("hint", "")
                    }
            logger.info(f"Dify schema: {schema}")
            return required_inputs
        except Exception as e:
            raise Exception(f"Failed to fetch Dify schema: {str(e)}")
    
    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Dify连接器操作
        """
        # 1. 检查配置参数 - 直接报错，不返回NEED_INPUT
        missing_config_params = self._check_missing_config_params(params)
        if missing_config_params:
            raise Exception(f"Missing required config parameters: {', '.join(missing_config_params)}")
        
        # 2. 解析最终使用的配置
        api_key = self._resolve_param("api_key", params)
        base_url = self._resolve_param("base_url", params).rstrip('/') # 去除末尾斜杠以防万一
        user = self._resolve_param("user", params) or "default_user"
        agent_id = self._resolve_param("agent_id", params)
        # content=self._resolve_param("content", params) or {}
        

        # 3. 检查输入参数 - 去掉params参数
        missing_inputs = self._check_missing_inputs(inputs)
        logger.info(f"Missing inputs: {missing_inputs}")
        if missing_inputs:

            from capabilities import get_capability
            from capabilities.context_resolver.interface import IContextResolverCapbility
            context_resolver:IContextResolverCapbility = get_capability("context_resolver", IContextResolverCapbility)
            filled_inputs,remaining_inputs = context_resolver.pre_fill_known_params_with_llm(missing_inputs, str(params))
            enhanced_inputs = context_resolver.enhance_param_descriptions_with_context(remaining_inputs, params)
            logger.info(f"Enhanced inputs: {enhanced_inputs}")
            completed_inputs = context_resolver.resolve_context(enhanced_inputs,agent_id)
            completed_inputs.update(filled_inputs)
            logger.info(f"Completed inputs: {completed_inputs}")
            also_missing_inputs={}
            for key in missing_inputs:
                if completed_inputs[key] is  None:
                    also_missing_inputs[key] = missing_inputs[key]
            if also_missing_inputs:
                
                # 返回需要补充输入参数的结果
                return {
                    "status": "NEED_INPUT",
                    "missing": also_missing_inputs,
                    "tool_schema": self._get_required_inputs()
                }
        
        # 4. 获取Dify配置 - 去掉workflow_id参数
        api_key = self._resolve_param("api_key", params)
        base_url = self._resolve_param("base_url", params)
        
        try:
            # 调用Dify API执行工作流
            url = f"{base_url}/workflows/run"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": completed_inputs,
                "response_mode": "blocking",
                "user": user
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=120)
            print(response.json())            
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Dify execution failed: {str(e)}")
            raise Exception(f"Dify execution failed: {str(e)}")
    
    def health_check(self, params: Dict[str, Any]) -> bool:
        """
        执行Dify健康检查
        """
        api_key = params.get("api_key")
        base_url = params.get("base_url", "https://api.dify.ai/v1")
        
        if not api_key:
            return False
        
        client = DifyClient(api_key, base_url)
        return client.health_check()
