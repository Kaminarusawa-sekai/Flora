"""Dify Schema解析器"""
from typing import Dict, Any, List


class DifySchemaParser:
    """
    用于解析Dify API返回的Schema信息
    """
    
    @staticmethod
    def parse_response_schema(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析Dify API响应的Schema
        
        Args:
            response: Dify API返回的响应
            
        Returns:
            解析后的Schema信息
        """
        schema = {
            'content': response.get('content', ''),
            'inputs': {},
            'metadata': {}
        }
        
        # 提取输入参数信息
        if 'inputs' in response:
            schema['inputs'] = response['inputs']
        
        # 提取元数据信息
        if 'metadata' in response:
            schema['metadata'] = response['metadata']
        
        # 提取工具调用信息
        if 'tool_calls' in response:
            schema['tool_calls'] = response['tool_calls']
        
        return schema
    
    @staticmethod
    def extract_required_fields(schema: Dict[str, Any]) -> List[str]:
        """
        从Schema中提取必填字段
        
        Args:
            schema: 解析后的Schema
            
        Returns:
            必填字段列表
        """
        required_fields = []
        
        # 从inputs中提取必填字段
        for field_name, field_info in schema.get('inputs', {}).items():
            if isinstance(field_info, dict) and field_info.get('required', False):
                required_fields.append(field_name)
        
        return required_fields
    
    @staticmethod
    def validate_params(params: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """
        验证参数是否包含所有必填字段
        
        Args:
            params: 待验证的参数
            required_fields: 必填字段列表
            
        Returns:
            验证结果，包含success和missing_fields字段
        """
        missing_fields = [field for field in required_fields if field not in params]
        
        return {
            'success': len(missing_fields) == 0,
            'missing_fields': missing_fields
        }
