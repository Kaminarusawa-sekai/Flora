#!/usr/bin/env python3
"""
Flora多智能体协作系统 - Agent客户端

用于通过API请求获取指定节点的子树
"""

import json
import logging
from typing import Dict, Any

import requests

logger = logging.getLogger(__name__)


class AgentClient:
    """
    Agent客户端类，用于与Flora API服务器交互
    """

    def __init__(self, base_url: str = "http://localhost:8003"):
        """
        初始化Agent客户端

        Args:
            base_url: API服务器基础URL，默认为http://localhost:8000
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })

    def get_agent_subtree(self, agent_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的Agent子树

        Args:
            agent_id: 根节点Agent ID

        Returns:
            子树结构，格式如下：
            {
                "agent_id": str,              # 节点Agent ID
                "meta": {                     # 节点元数据
                    "name": str,              # Agent名称
                    "type": str,              # Agent类型
                    "is_leaf": bool,          # 是否为叶子节点
                    "weight": float,          # 权重值
                    "description": str        # 描述信息
                    # 其他元数据字段...
                },
                "children": [                 # 子节点列表（递归结构）
                    {
                        "agent_id": str,
                        "meta": {},
                        "children": [...]
                    }
                    # 更多子节点...
                ]
            }

        Raises:
            requests.exceptions.RequestException: HTTP请求异常
            ValueError: API响应格式错误或请求失败
        """
        url = f"{self.base_url}/agents/tree/subtree/{agent_id}"

        try:
            logger.info("请求获取Agent子树，根节点ID: %s", agent_id)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()  # 抛出HTTP错误

            result = response.json()
            logger.debug("获取子树响应: %s", json.dumps(result, ensure_ascii=False))

            # 验证响应格式
            if not isinstance(result, dict):
                raise ValueError(f"无效的API响应格式: {type(result).__name__}")

            # 检查success字段
            if not result.get("success"):
                error_msg = result.get("error", "未知错误")
                raise ValueError(f"API请求失败: {error_msg}")

            # 验证data字段存在且为字典
            data = result.get("data")
            if not isinstance(data, dict):
                raise ValueError(f"无效的子树数据格式: {type(data).__name__}")

            return data

        except requests.exceptions.RequestException as e:
            logger.error("获取Agent子树失败: %s", str(e))
            raise
        except json.JSONDecodeError as e:
            logger.error("解析API响应失败: %s", str(e))
            raise ValueError(f"无效的JSON响应: {str(e)}") from e

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查API服务器

        Returns:
            健康检查结果
        """
        url = f"{self.base_url}/health"

        try:
            logger.info("请求健康检查")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("健康检查失败: %s", str(e))
            return {"status": "unhealthy", "error": str(e)}


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建客户端实例
    client = AgentClient("http://localhost:8000")

    try:
        # 示例：获取指定agent_id的子树
        # 请替换为实际存在的Agent ID
        test_agent_id = "example-agent-id"
        subtree = client.get_agent_subtree(test_agent_id)
        print(f"获取子树成功，根节点: {subtree.get('agent_id')}")
        print(f"子树结构: {json.dumps(subtree, ensure_ascii=False, indent=2)}")
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"请求失败: {str(e)}")
