from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from external.clients import HttpClient
from .base_connector import BaseConnector

logger = logging.getLogger(__name__)


class HttpConnector(BaseConnector):
    """
    HTTP连接器实现
    使用 BaseConnector._resolve_all_params() 统一补全流程：
    1. pre_fill_known_params_with_llm() - 从 context 提取已有值
    2. enhance_param_descriptions_with_context() - 增强描述
    3. resolve_semantic_pointers() - 语义指针补全（消解歧义）
    4. resolve_context() - text_to_sql 查询
    """

    def __init__(self):
        super().__init__()
    
    ##TODO：获取url
    def _check_missing_config_params(self, params: Dict[str, Any]) -> List[str]:
        """检查HTTP连接器缺失的配置参数"""
        required_params = ["url"]
        missing = []
        for param in required_params:
            if param not in params or params[param] is None or params[param] == "":
                missing.append(param)
        return missing

    def _get_required_params(self) -> List[str]:
        """获取HTTP必需配置参数列表"""
        return ["url"]

    def _check_missing_inputs(
        self,
        inputs: Dict[str, Any],
        args_schema: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        检查缺失的必填输入参数

        Args:
            inputs: 当前输入参数
            args_schema: 参数 schema 列表

        Returns:
            缺失参数字典 {param_name: description}
        """
        missing = {}
        for arg in args_schema:
            name = arg.get("name", "")
            required = arg.get("required", False)
            if required:
                value = inputs.get(name)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing[name] = arg.get("description", f"请提供 {name}")
        return missing

    def _coerce_value(self, value: Any, var_name: str = "") -> Any:
        """
        将值转换为合适的格式（参考 DifyConnector._coerce_text_value）
        """
        def normalize_candidate(candidate: Any) -> str:
            if candidate is None:
                return ""
            if isinstance(candidate, bool):
                return "true" if candidate else "false"
            if isinstance(candidate, (int, float)):
                if isinstance(candidate, float) and candidate.is_integer():
                    return str(int(candidate))
                return str(candidate)
            if isinstance(candidate, str):
                return candidate.strip()
            return str(candidate)

        def is_placeholder(text: str) -> bool:
            if not text:
                return True
            lowered = text.strip().lower()
            if lowered in {"id", "null", "none", "nan", ""}:
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
            # 优先提取 id 类型的值
            for item in value:
                if isinstance(item, dict) and "id" in item:
                    candidate = normalize_candidate(item.get("id"))
                    if candidate and candidate.isdigit():
                        return candidate
            first = value[0]
            if isinstance(first, dict):
                if "id" in first:
                    return normalize_candidate(first.get("id"))
                if len(first) == 1:
                    return normalize_candidate(next(iter(first.values())))
            return normalize_candidate(first)
        if isinstance(value, dict):
            if "id" in value:
                return normalize_candidate(value.get("id"))
            if len(value) == 1:
                return normalize_candidate(next(iter(value.values())))
        return normalize_candidate(value)

    

    def _build_request_data(
        self,
        args_schema: List[Dict[str, Any]],
        inputs: Dict[str, Any],
        method: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        根据参数 schema 构建请求数据

        Returns:
            (query_params, body_data) 元组
        """
        query_params = {}
        body_data = {}

        for arg in args_schema:
            name = arg.get("name", "")
            in_location = arg.get("in", "query")
            value = inputs.get(name)

            if value is not None and value != "":
                # 转换值格式
                coerced_value = self._coerce_value(value, name)
                if coerced_value is not None and coerced_value != "":
                    if in_location == "query":
                        query_params[name] = coerced_value
                    elif in_location == "body":
                        body_data[name] = coerced_value

        # 如果没有明确的 body 参数但有 inputs，且是 POST/PUT，将所有参数放入 body
        if method in ["POST", "PUT"] and not body_data and not args_schema:
            body_data = inputs

        return query_params, body_data

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行HTTP连接器操作

        使用 BaseConnector._resolve_all_params() 统一补全流程
        """
        # 1. 检查配置参数
        missing_config_params = self._check_missing_config_params(params)
        if missing_config_params:
            return {
                "status": "ERROR",
                "error": f"Missing required config parameters: {', '.join(missing_config_params)}"
            }

        # 获取配置
        url = params["url"]
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        timeout = params.get("timeout", 30)
        args_schema = params.get("args_schema", [])

        # 提取上下文（关键！）
        global_context = params.get("global_context", {})
        enriched_context = params.get("enriched_context", {})
        content = params.get("content", "")
        description = params.get("description", "")
        agent_id = params.get("agent_id", "")
        user_id = params.get("user_id", "")

        # 2. 检查缺失的输入参数
        if args_schema:
            missing_inputs = self._check_missing_inputs(inputs, args_schema)
            logger.info(f"Missing inputs: {missing_inputs}")

            if missing_inputs:
                # 构造完整上下文
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

                # 4. 调用统一补全方法（四步补全）
                filled_params, still_missing = self._resolve_all_params(
                    missing_params=missing_inputs,
                    context=full_context,
                    agent_id=agent_id,
                    user_id=user_id
                )

               
                # 合并所有输入
                 # 5. 合并结果
                completed_inputs = {**inputs, **filled_params}
                logger.info(f"Completed inputs: {completed_inputs}")

                # 6. 检查仍然缺失的参数
                also_missing = {}
                for key in missing_inputs:
                    value = completed_inputs.get(key)
                    if value is None or (isinstance(value, str) and value.strip() == ""):
                        also_missing[key] = missing_inputs[key]

                if also_missing:
                    return {
                        "status": "NEED_INPUT",
                        "missing": also_missing,
                        "completed": completed_inputs,
                        "tool_schema": args_schema
                    }

                inputs = completed_inputs

        # 7. 构建请求数据
        query_params, body_data = self._build_request_data(args_schema, inputs, method)

        # 如果没有 args_schema，使用原有逻辑
        if not args_schema:
            if method == "GET":
                query_params = inputs
            else:
                body_data = inputs

        # 8. 处理 URL 中的路径参数
        for key, value in inputs.items():
            if f"{{{key}}}" in url:
                url = url.replace(f"{{{key}}}", str(value))

        logger.info(f"HTTP {method} {url}, query={query_params}, body={body_data}")

        # 9. 创建 HTTP 客户端并执行请求
        http_client = HttpClient()

        try:
            if method == "GET":
                response = http_client.get(url, params=query_params, headers=headers, timeout=timeout)
            elif method == "POST":
                if query_params:
                    from urllib.parse import urlencode
                    url = f"{url}?{urlencode(query_params)}" if "?" not in url else f"{url}&{urlencode(query_params)}"
                response = http_client.post(url, json=body_data if body_data else None, headers=headers, timeout=timeout)
            elif method == "PUT":
                if query_params:
                    from urllib.parse import urlencode
                    url = f"{url}?{urlencode(query_params)}" if "?" not in url else f"{url}&{urlencode(query_params)}"
                response = http_client.put(url, json=body_data if body_data else None, headers=headers, timeout=timeout)
            elif method == "DELETE":
                response = http_client.delete(url, headers=headers, timeout=timeout)
            else:
                return {
                    "status": "ERROR",
                    "error": f"Unsupported HTTP method: {method}"
                }

            # 处理响应
            logger.info(f"HTTP response status={response.status_code}")

            if response.status_code >= 500:
                return {
                    "status": "FAILURE",
                    "error": f"HTTP service unavailable (status {response.status_code})"
                }
            elif response.status_code >= 400:
                return {
                    "status": "ERROR",
                    "error": f"HTTP client error (status {response.status_code})",
                    "details": response.text
                }

            # 成功响应
            try:
                result = response.json()
                return {"status": "SUCCESS", "result": result}
            except ValueError:
                return {
                    "status": "SUCCESS",
                    "result": {"text": response.text, "status_code": response.status_code}
                }

        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {
                "status": "FAILURE",
                "error": f"HTTP request failed: {str(e)}"
            }
        finally:
            http_client.close()

    def health_check(self, params: Dict[str, Any]) -> bool:
        """执行HTTP健康检查"""
        url = params.get("url")
        if not url:
            return False

        client = HttpClient()
        try:
            response = client.get(url)
            return response.status_code in [200, 201, 202, 204]
        finally:
            client.close()
