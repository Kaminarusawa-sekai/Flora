from typing import Dict, Any, List
import requests
import json
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
    
    def _coerce_text_value(self, value: Any, var_name: str = "") -> Any:
        def normalize_candidate(candidate: Any) -> str:
            if candidate is None:
                return ""
            if isinstance(candidate, bool):
                return "true" if candidate else "false"
            if isinstance(candidate, (int, float)):
                if isinstance(candidate, bool):
                    return str(candidate)
                if isinstance(candidate, float) and candidate.is_integer():
                    return str(int(candidate))
                return str(candidate)
            if isinstance(candidate, str):
                return candidate.strip()
            return str(candidate)

        def is_numeric_str(text: str) -> bool:
            if not text:
                return False
            if text.isdigit():
                return True
            if text.startswith("-") and text[1:].isdigit():
                return True
            return False

        def is_placeholder(text: str) -> bool:
            if not text:
                return True
            lowered = text.strip().lower()
            if lowered in {"id", "null", "none", "nan"}:
                return True
            if var_name and lowered == var_name.strip().lower():
                return True
            return False

        if value is None:
            return None
        if isinstance(value, str):
            candidate = value.strip()
            return "" if is_placeholder(candidate) else candidate
        if isinstance(value, list):
            if not value:
                return ""
            # Prefer numeric id-like values if present.
            for item in value:
                if isinstance(item, dict) and "id" in item:
                    candidate = normalize_candidate(item.get("id"))
                    if is_numeric_str(candidate):
                        return candidate
            for item in value:
                if isinstance(item, dict):
                    for v in item.values():
                        candidate = normalize_candidate(v)
                        if is_numeric_str(candidate):
                            return candidate
            first = value[0]
            if isinstance(first, dict):
                if "id" in first:
                    candidate = normalize_candidate(first.get("id"))
                    return "" if is_placeholder(candidate) else candidate
                if len(first) == 1:
                    candidate = normalize_candidate(next(iter(first.values())))
                    return "" if is_placeholder(candidate) else candidate
            candidate = normalize_candidate(first)
            return "" if is_placeholder(candidate) else candidate
        if isinstance(value, dict):
            if "id" in value:
                candidate = normalize_candidate(value.get("id"))
                return "" if is_placeholder(candidate) else candidate
            if len(value) == 1:
                candidate = normalize_candidate(next(iter(value.values())))
                return "" if is_placeholder(candidate) else candidate
            candidate = normalize_candidate(value)
            return "" if is_placeholder(candidate) else candidate
        candidate = normalize_candidate(value)
        return "" if is_placeholder(candidate) else candidate

    def _normalize_inputs_by_schema(
        self, inputs: Dict[str, Any], required_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not required_inputs:
            return inputs
        normalized = dict(inputs)
        for var_name, meta in required_inputs.items():
            if var_name not in normalized:
                continue
            field_type = meta.get("type")
            if field_type in ("text-input", "paragraph"):
                normalized[var_name] = self._coerce_text_value(normalized[var_name], var_name)
        return normalized

    @staticmethod
    def _is_id_like_param(name: str, label: str = "") -> bool:
        if name and name.lower().endswith("_id"):
            return True
        if name and name.lower() == "id":
            return True
        if label and "ID" in label.upper():
            return True
        return False
    
    def _check_missing_inputs(
        self, inputs: Dict[str, Any], required_inputs: Dict[str, Any] = None
        ) -> Dict[str, str]:
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
        except requests.exceptions.HTTPError as e:
            if getattr(e.response, "status_code", None) == 404:
                logger.warning("Dify schema endpoint not found; skipping schema fetch.")
                return {}
            raise Exception(f"Failed to fetch Dify schema: {str(e)}")

        except Exception as e:
            raise Exception(f"Failed to fetch Dify schema: {str(e)}")
    
    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Dify连接器操作
        使用 BaseConnector._resolve_all_params() 统一补全流程：
        1. pre_fill_known_params_with_llm() - 从 context 提取已有值
        2. enhance_param_descriptions_with_context() - 增强描述
        3. resolve_semantic_pointers() - 语义指针补全（消解歧义）
        4. resolve_context() - text_to_sql 查询
        """
        try:
            # 1. 检查配置参数 - 直接报错，不返回NEED_INPUT
            missing_config_params = self._check_missing_config_params(params)
            if missing_config_params:
                 return {
                    "status": "ERROR",
                    "error": f"Missing required config parameters: {', '.join(missing_config_params)}"
                }
            
            # 2. 解析最终使用的配置
            api_key = self._resolve_param("api_key", params)
            base_url = self._resolve_param("base_url", params).rstrip('/')
            user = self._resolve_param("user", params) or "default_user"
            agent_id = self._resolve_param("agent_id", params) or ""
            user_id = self._resolve_param("user_id", params) or ""
            content = self._resolve_param("content", params) or ""
            description = self._resolve_param("description", params) or ""

            # 3. 提取上下文（关键！）
            global_context = params.get("global_context", {})
            enriched_context = params.get("enriched_context", {})

             # 4. 获取 Dify schema 并检查缺失参数
            required_inputs = self._get_required_inputs(params)
            missing_inputs = self._check_missing_inputs(inputs, required_inputs)
            logger.info(f"Missing inputs: {missing_inputs}")
            if missing_inputs:

                
                 # 构造结构化上下文
                full_context = {
                    "global_context": global_context,
                    "enriched_context": enriched_context,
                    "content": content,
                    "description": description,
                    "agent_id": agent_id,
                    "user_id": user_id,
                    "original_inputs": inputs,
                }
                
                logger.info(f"Full context for param resolution: {full_context}")

                # 6. 调用统一补全方法（四步补全）
                filled_params, still_missing = self._resolve_all_params(
                    missing_params=missing_inputs,
                    context=full_context,
                    agent_id=agent_id,
                    user_id=user_id
                )

                # 7. 合并结果
                completed_inputs = {**inputs, **filled_params}
                completed_inputs = self._normalize_inputs_by_schema(
                    completed_inputs, required_inputs
                )
                logger.info(f"Completed inputs: {completed_inputs}")
                # 8. 检查仍然缺失的参数
                also_missing = {}
                for key in missing_inputs:
                    value = completed_inputs.get(key)
                    if value is None or (isinstance(value, str) and value.strip() == ""):
                        also_missing[key] = missing_inputs[key]

                if also_missing:
                    
                    # 返回需要补充输入参数的结果
                    return {
                        "status": "NEED_INPUT",
                        "missing": also_missing,
                        "completed": completed_inputs,
                        "tool_schema": self._get_required_inputs()
                    }
            
            # 4. 获取Dify配置 - 去掉workflow_id参数
            api_key = self._resolve_param("api_key", params)
            base_url = self._resolve_param("base_url", params)
        
        # try:
        #     # 调用Dify API执行工作流
        #     url = f"{base_url}/workflows/run"
        #     headers = {
        #         "Authorization": f"Bearer {api_key}",
        #         "Content-Type": "application/json"
        #     }
        #     payload = {
        #         "inputs": completed_inputs,
        #         "response_mode": "blocking",
        #         "user": user
        #     }
            
        #     response = requests.post(url, json=payload, headers=headers, timeout=120)
        #     print(response.json())            
        #     response.raise_for_status()
            
        #     return response.json()
        # except Exception as e:
        #     logger.error(f"Dify execution failed: {str(e)}")
        #     raise Exception(f"Dify execution failed: {str(e)}")


            # 4. 调用 Dify API
            url = f"{base_url}/workflows/run"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            completed_inputs = self._normalize_inputs_by_schema(
                completed_inputs, required_inputs
            )
            payload = {
                "inputs": completed_inputs,
                "response_mode": "blocking",
                "user": user
            }

            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)
                logger.info(f"Dify response: {response.json()}")
                content_type = response.headers.get("Content-Type", "")
                logger.info(
                    "Dify response status=%s content_type=%s body=%s",
                    response.status_code,
                    content_type,
                    response.text[:200],
                )
                if response.status_code >= 500:
                # 5xx 服务端错误 → 可重试
                    return {
                        "status": "FAILURE",
                        "error": f"Dify service unavailable (HTTP {response.status_code})"
                    }
                elif response.status_code >= 400:
                    # 4xx 客户端错误（如 invalid token, bad request）→ 不重试
                    try:
                        err_detail = response.json().get("message", response.text)
                    except:
                        err_detail = response.text
                    return {
                        "status": "ERROR",
                        "error": f"Dify client error (HTTP {response.status_code}): {err_detail}"
                    }

                result_data = response.json()

            except requests.exceptions.Timeout:
                return {"status": "FAILURE", "error": "Dify API request timed out"}
            except requests.exceptions.ConnectionError:
                return {"status": "FAILURE", "error": "Failed to connect to Dify service"}
            except requests.exceptions.RequestException as e:
                # 其他 requests 异常（如 DNS、SSL）通常也是临时问题
                return {"status": "FAILURE", "error": f"Network error when calling Dify: {str(e)}"}

            # 4. 解析 Dify 业务响应
            if not isinstance(result_data, dict) or "data" not in result_data:
                return {"status": "ERROR", "error": "Invalid Dify API response format"}

            workflow_data = result_data["data"]
            if workflow_data.get("status") != "succeeded":
                # Dify 工作流执行失败（如 prompt 错、节点异常）→ 通常是逻辑错误，不重试
                error_msg = workflow_data.get("error") or "Unknown execution error"
                return {"status": "ERROR", "error": f"Dify workflow failed: {error_msg}"}

            outputs = workflow_data.get("outputs", {})
            logger.info(f"Dify outputs: {outputs}")
            return {"status": "SUCCESS", "result": outputs}

        except Exception as e:
            logger.exception("Unexpected internal error in Dify connector")
            return {"status": "ERROR", "error": f"Internal system error: {str(e)}"}
    
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
