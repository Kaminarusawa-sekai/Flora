"""Qwen LLM适配器"""
from typing import Dict, Any, List, Optional
import requests
import json
from ..capability_base import CapabilityBase


class QwenAdapter(CapabilityBase):
    """
    Qwen大语言模型适配器
    提供与Qwen API交互的标准接口
    """
    
    def __init__(self, api_key: Optional[str] = None, api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"):
        """
        初始化Qwen适配器
        
        Args:
            api_key: API密钥
            api_base: API基础URL
        """
        super().__init__()
        self.api_key = api_key
        self.api_base = api_base
        self.default_model = "qwen-max"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else ""
        }
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'llm'
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        生成文本响应
        
        Args:
            prompt: 提示文本
            **kwargs: 额外参数
                - model: 使用的模型名称
                - temperature: 生成温度
                - max_tokens: 最大生成长度
                - top_p: 采样参数
                
        Returns:
            str: 生成的文本
        """
        model = kwargs.get('model', self.default_model)
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2048)
        top_p = kwargs.get('top_p', 0.9)
        
        # 构造请求体
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p
        }
        
        try:
            # 发送请求
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 解析响应
            if result.get('choices') and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                raise ValueError("No valid response from Qwen API")
        
        except Exception as e:
            # 处理异常
            print(f"Qwen API error: {str(e)}")
            return f"Error: {str(e)}"
    
    def generate_chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        基于对话历史生成响应
        
        Args:
            messages: 对话历史，格式为[{"role": "user/assistant/system", "content": "text"}, ...]
            **kwargs: 额外参数
                - model: 使用的模型名称
                - temperature: 生成温度
                - max_tokens: 最大生成长度
                
        Returns:
            Dict[str, Any]: 包含响应和元数据的字典
        """
        model = kwargs.get('model', self.default_model)
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2048)
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                "content": result.get('choices', [{}])[0].get('message', {}).get('content', ''),
                "model": result.get('model', model),
                "usage": result.get('usage', {}),
                "id": result.get('id', '')
            }
        
        except Exception as e:
            return {
                "content": f"Error: {str(e)}",
                "error": str(e)
            }
    
    def embedding(self, texts: List[str], model: str = "text-embedding-v1") -> List[List[float]]:
        """
        生成文本嵌入
        
        Args:
            texts: 文本列表
            model: 嵌入模型名称
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        # 注意：Qwen的embedding API可能有不同的端点
        # 这里使用通用的实现，实际应用中需要根据API文档调整
        
        payload = {
            "model": model,
            "input": texts
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/embeddings",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            embeddings = []
            for item in result.get('data', []):
                embeddings.append(item.get('embedding', []))
            
            return embeddings
        
        except Exception as e:
            print(f"Embedding error: {str(e)}")
            # 返回空嵌入
            return [[] for _ in texts]
    
    def set_api_key(self, api_key: str) -> None:
        """
        设置API密钥
        
        Args:
            api_key: 新的API密钥
        """
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"
    
    def set_default_model(self, model: str) -> None:
        """
        设置默认模型
        
        Args:
            model: 模型名称
        """
        self.default_model = model
    
    def get_supported_models(self) -> List[str]:
        """
        获取支持的模型列表
        
        Returns:
            List[str]: 支持的模型名称列表
        """
        return [
            "qwen-max",
            "qwen-plus",
            "qwen-turbo",
            "qwen-max-longcontext"
        ]
    
    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        """
        批量生成文本
        
        Args:
            prompts: 提示文本列表
            **kwargs: 额外参数
            
        Returns:
            List[str]: 生成的文本列表
        """
        results = []
        for prompt in prompts:
            results.append(self.generate(prompt, **kwargs))
        return results
