



'''
示例数据
 {

    "step": 2,

    "type": "AGENT",

    "executor": "compliance_checker",

    "description": "审核海报素材合规性（隐性依赖）",

    "params": {

      "check_rules": ["copyright", "sensitive_words"],

      "strict_mode": true

    },

    "is_parallel": false,

    "strategy_reasoning": "合规性检查是标准化的逻辑验证，不需要发散思维，单次执行即可确保结果。",

    "is_dependency_expanded": true,

    "original_parent": "poster_designer_v2"

  },

    "is_parallel": false,

    "strategy_reasoning": "邮件发送属于事务性操作，并行执行会导致收件人收到多封重复邮件，必须单次执行。",

    "is_dependency_expanded": false

  },

  {

    "step": 4,

    "type": "MCP",

    "executor": "nas_file_manager",

    "description": "归档海报文件",

    "params": {

      "action": "upload",

      "destination": "//server/public/2025/CNY",

      "source": "$step_1_output"

    },

    "is_parallel": false,

    "strategy_reasoning": "文件归档是确定性IO操作，无需多样性。",

    "is_dependency_expanded": false

  }


'''



"""任务规范定义"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskSpec(BaseModel):
    """
    单个子任务的规范定义（Pydantic 版本）
    示例数据
 {

    "step": 2,

    "type": "AGENT",

    "executor": "compliance_checker",

    "description": "审核海报素材合规性（隐性依赖）",

    "content": "审核海报素材合规性",

    "is_parallel": false,

    "strategy_reasoning": "合规性检查是标准化的逻辑验证，不需要发散思维，单次执行即可确保结果。",

    "is_dependency_expanded": true,

    "original_parent": "poster_designer_v2"

  },

    "is_parallel": false,

    "strategy_reasoning": "邮件发送属于事务性操作，并行执行会导致收件人收到多封重复邮件，必须单次执行。",

    "is_dependency_expanded": false

  },

  {

    "step": 4,

    "type": "MCP",

    "executor": "nas_file_manager",

    "description": "归档海报文件",

    "content": "归档海报文件",

    "is_parallel": false,

    "strategy_reasoning": "文件归档是确定性IO操作，无需多样性。",

    "is_dependency_expanded": false

  }
    """
    model_config = ConfigDict(extra='allow')
    step: int
    type: str
    executor: str
    description: str
    content: str
    user_id: Optional[str] = None

    # 新增控制字段
    is_parallel: bool = False
    strategy_reasoning: str = ""
    is_dependency_expanded: bool = False
    original_parent: Optional[str] = None


