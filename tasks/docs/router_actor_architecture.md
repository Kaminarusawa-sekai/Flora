# RouterActor和Redis集成 - DTO-Repo-Client架构说明

## 架构概述

本系统采用**DTO-Repo-Client**三层架构模式来管理Actor引用的持久化，具有清晰的职责划分和良好的可扩展性。

## 架构层次

```
┌─────────────────────────────────────────────────┐
│           ActorReferenceManager                 │  应用层
│  (common/utils/actor_reference_manager.py)      │  - 提供高级API
│  - serialize/deserialize                        │  - 序列化/反序列化
│  - 业务逻辑封装                                  │  - 统一入口
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│          ActorReferenceRepo                     │  Repository层
│  (external/repositories/actor_reference_repo.py)│  - CRUD操作
│  - save, get, delete                            │  - TTL管理
│  - refresh_ttl, update_heartbeat                │  - 心跳管理
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│             RedisClient                         │  Client层
│  (external/database/redis_client.py)            │  - Redis连接
│  - get, set, delete, expire                     │  - 基础操作
│  - 连接管理                                      │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│          ActorReferenceDTO                      │  DTO层
│  (common/types/actor_reference.py)              │  - 数据结构
│  - tenant_id, node_id                           │  - 序列化/反序列化
│  - actor_address, timestamps                    │
└─────────────────────────────────────────────────┘
```

## 核心组件

### 1. DTO层 - ActorReferenceDTO
**位置**: `common/types/actor_reference.py`

**职责**:
- 定义Actor引用的数据结构
- 提供与字典的转换方法
- 存储租户、节点、地址和时间戳信息

**属性**:
```python
@dataclass
class ActorReferenceDTO:
    tenant_id: str              # 租户ID
    node_id: str                # 节点ID
    actor_address: str          # 序列化后的ActorAddress
    created_at: datetime        # 创建时间
    expires_at: datetime        # 过期时间
    last_heartbeat: datetime    # 最后心跳时间
```

### 2. Client层 - RedisClient
**位置**: `external/database/redis_client.py`

**职责**:
- 管理Redis连接
- 提供基础的Redis操作
- 处理连接异常

**主要方法**:
- `get(key)` - 获取值
- `set(key, value, ttl)` - 设置值（带TTL）
- `delete(key)` - 删除键
- `expire(key, ttl)` - 设置过期时间

### 3. Repository层 - ActorReferenceRepo
**位置**: `external/repositories/actor_reference_repo.py`

**职责**:
- Actor引用的持久化管理
- CRUD操作
- TTL和心跳管理
- 内存降级方案

**主要方法**:
```python
# CRUD操作
save(dto, ttl)                  # 保存Actor引用
get(tenant_id, node_id)         # 获取Actor引用
delete(tenant_id, node_id)      # 删除Actor引用
exists(tenant_id, node_id)      # 检查是否存在

# TTL和心跳管理
refresh_ttl(tenant_id, node_id, ttl)     # 刷新TTL
update_heartbeat(tenant_id, node_id)     # 更新心跳时间

# 工具方法
create_key(tenant_id, node_id)  # 创建Redis键
is_redis_available()            # 检查Redis是否可用
```

**特性**:
- **双存储**: Redis + 内存，当Redis不可用时自动降级到内存模式
- **自动过期**: 内存模式也支持过期检查
- **JSON序列化**: DTO与Redis之间使用JSON序列化

### 4. Manager层 - ActorReferenceManager
**位置**: `common/utils/actor_reference_manager.py`

**职责**:
- 提供高级API
- ActorAddress序列化/反序列化
- 业务逻辑封装
- 统一入口

**主要方法**:
```python
# 序列化方法
serialize_address(addr)         # 序列化ActorAddress
deserialize_address(addr_str)   # 反序列化ActorAddress

# 业务方法
save_actor_reference(tenant_id, node_id, actor_address, ttl)
get_actor_reference(tenant_id, node_id)
delete_actor_reference(tenant_id, node_id)
refresh_actor_ttl(tenant_id, node_id, ttl)
update_heartbeat(tenant_id, node_id)

# 兼容性方法（为了保持与旧代码的兼容）
get_redis_client()              # 获取Redis客户端
set_with_ttl(key, value, ttl)   # 直接设置Redis键
get(key)                        # 直接获取Redis值
delete(key)                     # 直接删除Redis键
expire(key, ttl)                # 直接设置过期时间
```

## RouterActor集成

### RouterActor使用方式

RouterActor通过`actor_reference_manager`全局实例来管理Actor引用：

```python
from common.utils.actor_reference_manager import actor_reference_manager

class RouterActor(Actor):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("RouterActor")

        # 使用工具类
        self.use_redis = actor_reference_manager.is_redis_available()

        # 如果Redis不可用，使用内存字典作为备选
        if not self.use_redis:
            self._memory_dict = {}
```

### 注册Actor引用

```python
def _handle_actor_registration(self, msg, sender):
    tenant_id = msg.get("tenant_id")
    node_id = msg.get("node_id")

    # 序列化地址
    addr_str = actor_reference_manager.serialize_address(sender)

    # 保存到Redis（使用兼容性方法）
    key = actor_reference_manager.create_redis_key("session", tenant_id, node_id)
    actor_reference_manager.set_with_ttl(key, addr_str, ttl=3600)
```

### 获取Actor引用

```python
def _get_actor_address(self, key):
    # 从Redis获取
    addr_str = actor_reference_manager.get(key)

    if addr_str:
        # 反序列化
        return actor_reference_manager.deserialize_address(addr_str)

    return None
```

## SessionActor集成

### 心跳机制

SessionActor定期向RouterActor发送心跳，RouterActor刷新TTL：

```python
def _handle_heartbeat(self, msg, sender):
    tenant_id = msg.get("tenant_id")
    node_id = msg.get("node_id")

    # 刷新TTL
    actor_reference_manager.refresh_actor_ttl(tenant_id, node_id, ttl=3600)
```

## 配置

### Redis配置 (config.py)

```python
REDIS_HOST = 'PROD.REDIS8'
REDIS_PORT = 6379
REDIS_DATABASE = 0
REDIS_PASSWORD = 'lanba888'
```

### 默认TTL

- **默认值**: 3600秒 (1小时)
- **心跳间隔**: 3000秒 (50分钟)

## 降级方案

### Redis不可用时的处理

1. **自动检测**: 初始化时自动检测Redis连接状态
2. **内存降级**: Redis不可用时自动使用内存字典存储
3. **过期管理**: 内存模式也支持TTL和过期检查
4. **日志记录**: 清晰记录降级状态

### 内存模式特点

- **结构**: `{key: {"value": str, "expires_at": datetime}}`
- **过期检查**: 每次读取时检查过期时间
- **自动清理**: 读取到过期数据时自动删除

## 测试

### 运行测试

```bash
python test_router.py
```

### 测试内容

1. **Redis Client测试** - 测试基础Redis连接和操作
2. **ActorReferenceRepo测试** - 测试Repository层CRUD操作
3. **ActorReferenceManager测试** - 测试Manager层业务逻辑
4. **RouterActor测试** - 测试完整的Actor路由流程

## 优点

### 1. 清晰的职责分离
- **DTO**: 只负责数据结构
- **Client**: 只负责连接管理
- **Repo**: 只负责持久化操作
- **Manager**: 只负责业务逻辑

### 2. 易于测试
- 每一层都可以独立测试
- Mock更简单
- 单元测试覆盖率更高

### 3. 易于扩展
- 更换存储后端：只需修改Repo层
- 添加新功能：在Manager层添加
- 优化序列化：只需修改Manager层

### 4. 降级方案
- Redis不可用时自动降级
- 不影响系统正常运行
- 提高系统可用性

### 5. 兼容性
- 保留兼容性方法
- 旧代码无需大幅修改
- 平滑过渡

## 最佳实践

1. **使用Manager层API**: 业务代码应使用Manager层提供的高级API，而不是直接操作Repo
2. **处理None**: 所有获取操作都可能返回None，需要妥善处理
3. **异常处理**: 每层都应有适当的异常处理和日志记录
4. **TTL设置**: 根据业务需求合理设置TTL时间
5. **心跳频率**: 心跳间隔应小于TTL，建议为TTL的80%-90%

## 未来优化方向

1. **连接池**: 使用Redis连接池提高性能
2. **批量操作**: 添加批量保存/获取方法
3. **缓存策略**: 添加本地缓存减少Redis访问
4. **监控**: 添加性能监控和告警
5. **分布式锁**: 使用Redis实现分布式锁机制
