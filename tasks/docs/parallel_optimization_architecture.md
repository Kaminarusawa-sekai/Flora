# 并行任务优化架构说明

## 概述

基于**Optuna + LLM**的并行任务优化系统，用于自动发现和优化任务参数。该系统整合了维度解析（DimensionParser）和并行优化（OptunaOptimizer），实现了智能的参数空间探索。

## 核心组件

### 1. DimensionParserCapability (`capabilities/dimension/dimension_parser.py`)

使用LLM自动发现和解析优化维度。

#### 主要功能

**discover_schema()** - 自动发现优化维度
```python
# 输入：用户目标
user_goal = "生成一篇高质量的产品文案"

# 输出：维度定义和初始向量
{
  "dimensions": [
    {"name": "temperature", "description": "控制生成随机性"},
    {"name": "prompt_style", "description": "提示词风格"},
    {"name": "creativity", "description": "创造性水平"}
  ],
  "initial_vector": [0.1, -0.3, 0.5]
}
```

**vector_to_instruction()** - 向量转换为自然语言指令
```python
# 输入：参数向量
vector = [0.8, -0.5, 0.3]

# 输出：可执行指令
"使用更正式的语气，提高创造性，减少示例数量，重点强调可靠性。"
```

**output_to_score()** - 评估输出并打分
```python
# 输入：执行输出
output = "产品文案内容..."

# 输出：评分和反馈
{
  "score": 0.85,
  "feedback": "创意不错，但未突出核心卖点"
}
```

### 2. OptunaOptimizer (`capabilities/parallel/optuna_optimizer.py`)

基于Optuna的参数空间优化器。

#### 主要功能

- **suggest_parameters()**: 批量建议参数组合
- **update_optimization_results()**: 更新优化结果
- **get_best_parameters()**: 获取最佳参数
- **get_optimization_history()**: 获取优化历史

### 3. OptimizationOrchestrator (`capabilities/parallel/optuna_optimizer.py`)

协调LLM与优化器的集成。

#### 主要功能

- **discover_optimization_dimensions()**: 自动发现维度
- **get_optimization_instructions()**: 生成优化指令批次
- **process_execution_results()**: 处理执行结果并更新优化器

### 4. ParallelTaskAggregatorActor (`capability_actors/parallel_task_aggregator_actor.py`)

并行任务聚合器，支持两种模式：

1. **简单重复模式**: 多次执行相同任务，聚合结果
2. **优化模式**: 使用Optuna+LLM自动优化任务参数

## 优化流程

### 完整流程图

```
┌──────────────────────────────────────────────────────────────┐
│                   ParallelTaskAggregatorActor                │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────┐
            │ 1. 检查optimization_enabled │
            └───────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
         简单重复模式              优化模式
                │                       │
                ▼                       ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │  重复执行N次任务  │    │ 2. 创建Orchestrator   │
    │  聚合结果        │    └──────────────────────┘
    └──────────────────┘              │
                                      ▼
                        ┌──────────────────────────┐
                        │ 3. 使用DimensionParser   │
                        │    发现优化维度          │
                        └──────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ 4. 生成优化指令批次      │
                        │    (Optuna建议参数)      │
                        └──────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ 5. 执行任务              │
                        │    (带优化指令)          │
                        └──────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ 6. DimensionParser评估   │
                        │    输出并打分            │
                        └──────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ 7. 更新Optuna优化器      │
                        └──────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────┐
                        │ 8. 检查是否继续优化     │
                        └──────────────────────────┘
                                      │
                        ┌─────────────┴────────────┐
                        │                          │
                    继续下一轮              完成优化
                        │                          │
                        └──────────┐               ▼
                                   │    ┌─────────────────┐
                                   └──► │ 返回最佳参数    │
                                        └─────────────────┘
```

### 详细步骤

#### 步骤 1: 启用优化模式

```python
# 创建任务规范
task_spec = TaskSpec(
    task_id="optimize_task",
    type="dify",  # 或其他任务类型
    parameters={
        "optimization_enabled": True,  # 启用优化
        "user_goal": "生成高质量的产品文案",
        "optimization_direction": "maximize",  # 优化方向
        "batch_size": 3,  # 每轮并行执行数
        # 其他任务参数...
    },
    repeat_count=15,  # 总共执行15次（5轮 x 3次/轮）
    aggregation_strategy="best"
)

# 发送请求
repeat_request = RepeatTaskRequest(
    source=my_address,
    destination=parallel_aggregator,
    spec=task_spec
)
```

#### 步骤 2: 维度发现

DimensionParser使用LLM分析用户目标，自动发现优化维度：

```python
# LLM 提示词示例
"""
用户目标：生成高质量的产品文案

请分析该任务，确定一组最关键的可调参数（称为"优化维度"）。

输出格式（严格 JSON）：
{
  "dimensions": [
    {"name": "temperature", "description": "控制生成随机性"},
    {"name": "creativity_level", "description": "创造性水平"},
    {"name": "formal_tone", "description": "正式程度"}
  ],
  "initial_vector": [0.7, 0.5, 0.3]
}
"""
```

#### 步骤 3: 生成优化指令

Optuna建议参数向量 → DimensionParser转换为指令：

```python
# Optuna建议向量
trial_1_vector = [0.8, 0.6, 0.2]
trial_2_vector = [0.5, 0.9, 0.7]
trial_3_vector = [0.3, 0.4, 0.8]

# 转换为自然语言指令
instruction_1 = "高温度采样，适度创造性，低正式度"
instruction_2 = "中温度采样，高创造性，高正式度"
instruction_3 = "低温度采样，低创造性，极高正式度"
```

#### 步骤 4: 并行执行

每个试验（trial）并行执行任务：

```python
# Trial 1
task_params_1 = {
    "optimization_instruction": instruction_1,
    "optimization_vector": [0.8, 0.6, 0.2],
    "trial_number": 0,
    # 原始任务参数...
}

# 执行并收集输出
output_1 = execute_task(task_params_1)
```

#### 步骤 5: 评估和打分

DimensionParser评估每个输出：

```python
# LLM 评估提示词
"""
用户目标：生成高质量的产品文案

原始输出：
[产品文案内容...]

请评估此输出在多大程度上达成了用户目标，给出 0.0 ~ 1.0 的分数。

输出格式（严格 JSON）：
{
  "score": 0.85,
  "feedback": "文案创意性强，但正式程度略低"
}
"""
```

#### 步骤 6: 更新优化器

将评分反馈给Optuna：

```python
# 更新优化结果
trials_results = [
    (trial_1, score_1),  # 0.85
    (trial_2, score_2),  # 0.72
    (trial_3, score_3),  # 0.68
]

optimizer.update_optimization_results(trials_results)
```

#### 步骤 7: 迭代优化

重复步骤3-6，直到达到最大轮数或满足停止条件。

#### 步骤 8: 返回最佳结果

```python
best_params = optimizer.get_best_parameters()
# {
#   "vector": [0.8, 0.6, 0.2],
#   "value": 0.85,
#   "trial_number": 0
# }
```

## 使用示例

### 示例 1: 文案优化

```python
# 定义任务
task_spec = TaskSpec(
    task_id="copywriting_optimization",
    type="dify",
    parameters={
        "optimization_enabled": True,
        "user_goal": "生成吸引人的电商产品文案",
        "optimization_direction": "maximize",
        "batch_size": 4,
        "workflow_id": "copywriting_workflow",
        "base_product_info": {
            "name": "智能手表",
            "features": ["健康监测", "长续航", "防水"]
        }
    },
    repeat_count=20,  # 5轮 x 4次/轮
    aggregation_strategy="best"
)

# 执行优化
# ParallelTaskAggregatorActor会：
# 1. 使用LLM发现优化维度（如：语气、重点、长度等）
# 2. Optuna探索参数空间
# 3. 每轮执行4个不同的文案生成任务
# 4. LLM评估每个文案的质量
# 5. 持续优化5轮
# 6. 返回最佳文案及其参数
```

### 示例 2: 数据分析优化

```python
task_spec = TaskSpec(
    task_id="analysis_optimization",
    type="mcp",
    parameters={
        "optimization_enabled": True,
        "user_goal": "生成清晰准确的数据分析报告",
        "optimization_direction": "maximize",
        "batch_size": 3,
        "dataset": "sales_data.csv",
        "analysis_type": "trend_analysis"
    },
    repeat_count=15,
    aggregation_strategy="best"
)
```

## 事件追踪

系统发布以下事件用于监控和调试：

```python
# 优化启动
OPTIMIZATION_STARTED {
    "user_goal": "...",
    "dimensions": [...],
    "batch_size": 3
}

# 优化进度（每轮）
OPTIMIZATION_TRIGGERED {
    "round": 2,
    "best_params": {...},
    "trial_count": 6
}

# 优化完成
OPTIMIZATION_COMPLETED {
    "best_parameters": {...},
    "total_rounds": 5,
    "total_trials": 15
}
```

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `optimization_enabled` | bool | False | 是否启用优化模式 |
| `user_goal` | str | 必填 | 用户目标描述 |
| `optimization_direction` | str | "maximize" | 优化方向（maximize/minimize） |
| `batch_size` | int | 3 | 每轮并行执行数 |
| `repeat_count` | int | 必填 | 总执行次数 |
| `max_optimization_rounds` | int | 5 | 最大优化轮数 |

## 优势

1. **自动维度发现**: 无需手动定义参数空间，LLM自动识别关键维度
2. **自然语言交互**: 使用自然语言指令而非数值参数，更易理解
3. **智能评估**: LLM理解任务目标，提供准确的质量评分
4. **高效探索**: Optuna使用贝叶斯优化，快速收敛到最优区域
5. **并行执行**: 每轮并行执行多个试验，加速优化过程
6. **可追踪**: 完整的事件发布，方便监控和调试

## 限制和注意事项

1. **LLM调用开销**: 每个试验需要2-3次LLM调用（维度发现、指令生成、结果评估）
2. **评分一致性**: LLM评分可能存在主观性，需要清晰的评估标准
3. **维度数量**: 建议维度数≤5，过多维度会降低优化效率
4. **执行成本**: 每轮batch_size个任务并行执行，注意资源消耗
5. **API配额**: 确保OpenAI API有足够配额

## 扩展和改进

1. **自定义评分函数**: 结合业务指标（如点击率、转化率）
2. **多目标优化**: 同时优化多个指标（质量、成本、时间等）
3. **预算约束**: 设置最大LLM调用次数或总成本上限
4. **Early Stopping**: 当性能停止改善时提前终止
5. **Transfer Learning**: 跨任务共享优化经验

## 文件清单

### 新增/修改文件
- `capability_actors/parallel_task_aggregator_actor.py` - 整合优化流程
- `docs/parallel_optimization_architecture.md` - 本文档

### 使用的现有文件
- `capabilities/dimension/dimension_parser.py` - 维度解析
- `capabilities/parallel/optuna_optimizer.py` - Optuna优化器
- `capabilities/parallel/parallel_optimization_interface.py` - 优化接口

## 常见问题

### Q: 如何调整优化速度和质量的平衡？

A: 通过以下参数调整：
- `batch_size`: 增加并行度，加快速度但增加成本
- `max_optimization_rounds`: 增加轮数，提高质量但延长时间
- `repeat_count`: 总试验次数，影响探索充分性

### Q: 优化结果不理想怎么办？

A: 检查以下几点：
1. `user_goal`是否清晰明确
2. 初始参数空间是否合理
3. 评分标准是否准确反映质量
4. 是否需要更多轮次探索

### Q: 如何降低LLM调用成本？

A: 可以：
1. 减少`batch_size`和轮数
2. 使用更便宜的模型（如GPT-3.5）
3. 缓存常见的维度发现结果
4. 对于相似任务复用优化结果

## 示例输出

```json
{
  "type": "optimization_result",
  "task_id": "copywriting_optimization",
  "success": true,
  "best_parameters": {
    "vector": [0.85, 0.62, 0.35],
    "value": 0.92,
    "trial_number": 12
  },
  "optimization_history": [
    {
      "trial_number": 0,
      "value": 0.75,
      "vector": [0.5, 0.5, 0.5],
      ...
    },
    ...
  ],
  "total_rounds": 5,
  "total_trials": 15
}
```
