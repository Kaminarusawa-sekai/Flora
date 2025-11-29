# 循环任务优化架构说明

## 概述

实现了一个**异步反馈环（Asynchronous Feedback Loop）**架构，用于循环任务的自动优化。该架构将执行（Execution）和优化（Optimization）分离为两个独立的生命周期。

## 核心架构

### 三大角色

1. **LoopSchedulerActor**: 负责"何时做"（Timing）和"存配置"（State）
   - 管理循环任务的调度
   - 存储任务配置和优化参数
   - 与RabbitMQ集成，触发定时执行

2. **AgentActor**: 负责"做什么"（Execution）
   - 执行具体的任务逻辑
   - 发送执行结果反馈给OptimizerActor
   - 应用优化后的参数执行任务

3. **OptimizerActor**: 负责"怎么做得更好"（Reflection & Tuning）
   - 收集并分析执行历史
   - 生成优化建议
   - 更新任务参数

### 新增组件

#### OptimizerActor (`capability_actors/optimizer_actor.py`)

职责：
- 管理每个循环任务的优化器实例
- 收集执行历史和反馈
- 生成优化建议
- 更新任务参数

支持的消息类型：
- `register_optimization`: 注册需要优化的任务
- `execution_feedback`: 接收执行反馈
- `request_optimization`: 手动请求优化
- `get_optimization_stats`: 获取优化统计
- `reset_optimizer`: 重置优化器
- `unregister_optimization`: 取消注册

#### 优化能力 (`capabilities/optimization/`)

使用现有的优化能力：
- **OptimizationInterface**: 优化方法抽象接口
- **MultiFeatureOptimizer**: 多特征优化器实现
  - 使用知识库存储和应用优化规则
  - 支持成功/失败模式学习
  - 支持状态保存和加载

## 工作流程

### 1. 注册循环任务（启用优化）

```python
# AgentActor 向 LoopSchedulerActor 注册循环任务
loop_scheduler.send({
    "type": "register_loop_task",
    "task_id": "daily_report",
    "interval_sec": 86400,  # 每天执行
    "message": {...},
    "optimization_enabled": True,  # 启用优化
    "optimization_config": {
        "default_parameters": {
            "batch_size": 100,
            "timeout": 30
        },
        "optimization_interval": 10,  # 每执行10次优化一次
        "constraints": {
            "batch_size": (50, 500),
            "timeout": (10, 120)
        }
    }
})
```

### 2. LoopSchedulerActor 处理注册

```python
# LoopSchedulerActor
- 保存任务到任务仓库
- 标记 optimization_enabled[task_id] = True
- 向 OptimizerActor 发送注册请求
```

### 3. 任务执行

```python
# RabbitMQ 触发 → LoopSchedulerActor → AgentActor
- LoopSchedulerActor 构造执行消息
- 如果有优化参数，添加到消息中
- 发送给 AgentActor 执行
```

### 4. 执行反馈

```python
# AgentActor 执行完成后
- 计算执行分数 (基于时间、成功率、结果质量)
- 构建执行记录
- 发送给 OptimizerActor
```

### 5. 优化学习

```python
# OptimizerActor
- 收集执行历史
- 使用 MultiFeatureOptimizer 学习
- 每 N 次执行后触发优化
- 发送优化参数给 LoopSchedulerActor
```

### 6. 应用优化

```python
# LoopSchedulerActor
- 接收优化参数
- 保存到 optimized_parameters[task_id]
- 下次执行时应用新参数
```

## 消息流图

```
┌─────────────────┐
│  LoopScheduler  │
│     Actor       │
└────────┬────────┘
         │ 1. 注册任务(启用优化)
         ▼
┌─────────────────┐
│   Optimizer     │◄─────┐
│     Actor       │      │ 5. 学习并优化
└────────┬────────┘      │
         │ 6. 优化参数   │
         ▼               │
┌─────────────────┐      │
│  LoopScheduler  │      │
│     Actor       │      │
└────────┬────────┘      │
         │ 3. 执行任务   │
         ▼               │
┌─────────────────┐      │
│   Agent Actor   │──────┘
│   (执行并反馈)   │ 4. 执行反馈
└─────────────────┘
```

## 事件类型

新增事件类型（`events/event_types.py`）：

```python
# 优化相关事件
OPTIMIZATION_REGISTERED       # 注册优化
OPTIMIZATION_UNREGISTERED     # 取消注册
OPTIMIZATION_LEARNED          # 学习反馈
OPTIMIZATION_TRIGGERED        # 触发优化
OPTIMIZATION_RESET            # 重置优化器
OPTIMIZATION_APPLIED          # 应用优化结果

# 循环任务事件
LOOP_TASK_REGISTERED         # 循环任务注册
LOOP_TASK_TRIGGERED          # 循环任务触发
TASK_TRIGGERED               # 任务触发（通用）
TASK_UPDATED                 # 任务更新
```

## 使用示例

### 创建启用优化的循环任务

```python
# 1. 向 LoopSchedulerActor 注册
loop_scheduler.send({
    "type": "register_loop_task",
    "task_id": "optimization_demo",
    "interval_sec": 3600,
    "message": {
        "original_task": {"description": "数据处理任务"}
    },
    "optimization_enabled": True,
    "optimization_config": {
        "default_parameters": {
            "chunk_size": 1000,
            "parallel_workers": 4
        },
        "optimization_interval": 5,
        "constraints": {
            "chunk_size": (100, 10000),
            "parallel_workers": (1, 16)
        }
    }
})
```

### 手动请求优化

```python
# 向 OptimizerActor 发送请求
optimizer.send({
    "type": "request_optimization",
    "task_id": "optimization_demo"
})
```

### 查看优化统计

```python
# 获取所有任务的优化统计
optimizer.send({
    "type": "get_optimization_stats"
})

# 获取特定任务的统计
optimizer.send({
    "type": "get_optimization_stats",
    "task_id": "optimization_demo"
})
```

## 优化策略

### 执行分数计算

`AgentActor._calculate_execution_score()` 计算执行分数：

- 基础分数: 0.7
- 执行时间调整:
  - < 1秒: +0.2
  - > 10秒: -0.2
- 结果质量调整（如果提供）
- 最终范围: 0.0 - 1.0

### 优化学习

`MultiFeatureOptimizer` 使用知识库学习：

- **成功模式** (score > 0.7): 增加参数值 (factor: 1.1)
- **失败模式** (score ≤ 0.7): 减少参数值 (factor: 0.9)
- 考虑约束条件，确保参数在允许范围内

## 优势

1. **异步非阻塞**: 优化过程不影响任务执行
2. **持续学习**: 从每次执行中学习，不断改进
3. **可配置**: 灵活的优化间隔和参数约束
4. **可追踪**: 完整的事件发布，方便监控和调试
5. **独立生命周期**: 执行、调度、优化各司其职

## 扩展点

1. **自定义优化器**: 实现 `OptimizationInterface` 接口
2. **自定义分数计算**: 重写 `_calculate_execution_score()`
3. **多目标优化**: 扩展 `MultiFeatureOptimizer` 支持多个优化目标
4. **A/B测试**: 在 `OptimizerActor` 中实现参数对比实验

## 注意事项

1. **内存管理**: 执行历史会累积，需要定期清理或限制大小
2. **参数验证**: 确保优化后的参数符合业务逻辑
3. **性能影响**: 优化计算应该异步进行，不阻塞任务执行
4. **错误处理**: 优化失败不应影响任务正常执行

## 文件清单

### 新增文件
- `capability_actors/optimizer_actor.py` - OptimizerActor实现
- `docs/optimization_architecture.md` - 本文档

### 修改文件
- `events/event_types.py` - 添加优化相关事件
- `capability_actors/loop_scheduler_actor.py` - 支持优化标记和参数应用
- `agents/agent_actor.py` - 添加优化反馈逻辑

### 使用的现有文件
- `capabilities/optimization/optimization_interface.py` - 优化接口
- `capabilities/optimization/multi_feature_optimizer.py` - 优化实现

## 后续改进

1. **持久化**: 将优化器状态保存到数据库
2. **可视化**: 提供优化趋势图表
3. **智能触发**: 根据性能变化动态调整优化频率
4. **多策略**: 支持不同的优化算法（贝叶斯优化、遗传算法等）
