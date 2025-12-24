# User & Session 设计方案

## 一、核心概念澄清：User vs Session

| 概念   | 含义                | 生命周期                | 示例                          |
|-------|---------------------|-------------------------|-------------------------------|
| User  | 真实用户身份        | 跨多个会话，长期存在    | user_id = "u123"              |
| Session | 一次对话上下文      | 几分钟~几小时，可配置   | session_id = "s456"           |

✅ 关键点：一个 User 可以有多个 Session；一个 Session 必须属于一个 User（即使是匿名用户，也可视为临时 User）。

## 二、当前设计分析

### 优势
1. 已定义 `UserInputDTO`，包含 `session_id` 和 `user_id` 字段
2. 已实现对话状态管理机制
3. 已有数据库存储层，支持对话状态持久化

### 不足
1. `DialogStateDTO` 缺少 `user_id` 字段，无法关联到具体用户
2. 对话状态管理仅基于 `session_id`，未考虑用户维度
3. 缺少前端查询接口
4. 缺少会话过期策略
5. 匿名用户处理机制不明确

## 三、设计方案

### 1. 设计原则

- **明确区分**：清晰区分 User（用户身份）和 Session（对话上下文）
- **强关联**：每个 Session 必须关联到一个 User
- **灵活性**：支持匿名用户、临时用户和正式用户
- **可扩展**：便于后续添加用户个性化、多设备同步等功能
- **安全性**：保护用户隐私，防止越权访问

### 2. 数据模型改进

#### 2.1 DialogTurn 改进

```python
class DialogTurn(BaseModel):
    role: str
    utterance: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    enhanced_utterance: Optional[str] = None
    session_id: str  # 新增：关联到具体会话
    user_id: str  # 新增：关联到具体用户
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "utterance": self.utterance,
            "timestamp": self.timestamp,
            "enhanced_utterance": self.enhanced_utterance,
            "session_id": self.session_id,
            "user_id": self.user_id
        }
```

#### 2.2 DialogStateDTO 改进

```python
class DialogStateDTO(BaseModel):
    """💬 [5. DialogStateDTO] 全局会话状态"""
    session_id: str
    user_id: str  # 新增：关联到具体用户
    current_intent: Optional[str] = None
    # ... 其他字段保持不变
```

#### 2.3 数据库表设计

##### 2.3.1 dialog_turns 表（与现有表结构关联）

| 字段名 | 类型 | 描述 |
|-------|------|------|
| id | INTEGER | 主键，自增 |
| session_id | VARCHAR(36) | 会话ID，外键 |
| user_id | VARCHAR(36) | 用户ID，外键 |
| role | VARCHAR(20) | 角色（user/system） |
| utterance | TEXT | 对话内容 |
| timestamp | REAL | 时间戳 |
| enhanced_utterance | TEXT | 增强型对话内容 |
| PRIMARY KEY | (id) | |
| INDEX | (session_id, timestamp) | 按会话ID和时间戳索引 |
| INDEX | (user_id, timestamp) | 按用户ID和时间戳索引 |

##### 2.3.2 dialog_state 表

| 字段名 | 类型 | 描述 |
|-------|------|------|
| session_id | VARCHAR(36) | 主键 |
| user_id | VARCHAR(36) | 外键，关联到用户表 |
| current_intent | VARCHAR(50) | 当前意图 |
| last_updated | DATETIME | 最后更新时间 |
| # 其他字段... | | |

### 3. 前端查询接口设计

#### 3.1 查询当前 Session 信息

```http
GET /api/v1/session/{session_id}
```

**返回示例：**
```json
{
  "session_id": "s456",
  "user_id": "u123",
  "created_at": "2025-12-24T01:00:00Z",
  "last_active": "2025-12-24T01:15:00Z",
  "current_intent": "IDLE_CHAT",
  "waiting_for_confirmation": false,
  "active_task_draft": null
}
```

#### 3.2 查询用户所有活跃 Sessions

```http
GET /api/v1/user/{user_id}/sessions
```

**返回示例：**
```json
[
  {
    "session_id": "s456",
    "last_active": "2025-12-24T01:15:00Z",
    "current_intent": "IDLE_CHAT"
  },
  {
    "session_id": "s789",
    "last_active": "2025-12-24T01:10:00Z",
    "current_intent": "CREATE_TASK"
  }
]
```

#### 3.3 绑定用户到会话（匿名转正式）

```http
POST /api/v1/session/{session_id}/bind-user
Content-Type: application/json

{
  "user_id": "u123"  # 正式用户ID
}
```

#### 3.4 查询会话对话历史

```http
GET /api/v1/session/{session_id}/history?limit=20&offset=0
```

**返回示例：**
```json
[
  {
    "id": 1,
    "session_id": "s456",
    "user_id": "u123",
    "role": "user",
    "utterance": "你好",
    "timestamp": 1734999000.0,
    "enhanced_utterance": null
  },
  {
    "id": 2,
    "session_id": "s456",
    "user_id": "u123",
    "role": "system",
    "utterance": "您好！有什么可以帮助您的吗？",
    "timestamp": 1734999001.0,
    "enhanced_utterance": null
  }
]
```

#### 3.5 查询用户所有对话历史

```http
GET /api/v1/user/{user_id}/history?limit=20&offset=0
```

**返回示例：**
```json
[
  {
    "session_id": "s456",
    "turns": [
      // 对话轮次列表
    ]
  },
  {
    "session_id": "s789",
    "turns": [
      // 对话轮次列表
    ]
  }
]
```

### 4. 代码集成建议

#### 4.1 ContextManager 改进

```python
class CommonContextManager(IContextManagerCapability):
    # ... 其他方法保持不变
    
    def add_turn(self, turn: DialogTurn) -> int:
        """添加一个对话轮次到上下文"""
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.save_turn(turn)
    
    def get_turns_by_session(self, session_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        """根据会话ID获取对话轮次"""
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.get_turns_by_session(session_id, limit, offset)
    
    def get_turns_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        """根据用户ID获取对话轮次"""
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.get_turns_by_user(user_id, limit, offset)
    
    def update_turn_user_id(self, session_id: str, old_user_id: str, new_user_id: str) -> bool:
        """更新会话中所有轮次的用户ID（用于匿名转正式）"""
        if not self.repo:
            raise ValueError("Context manager not initialized")
        return self.repo.update_turns_user_id(session_id, old_user_id, new_user_id)
```

#### 4.2 DialogRepository 改进

```python
class DialogRepository:
    def _create_table(self):
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dialog_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    utterance TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    enhanced_utterance TEXT
                )
            ''')
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_timestamp ON dialog_turns(session_id, timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_timestamp ON dialog_turns(user_id, timestamp)')
            conn.commit()
        finally:
            self.pool.return_connection(conn)
    
    def save_turn(self, turn: DialogTurn) -> int:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO dialog_turns (session_id, user_id, role, utterance, timestamp, enhanced_utterance)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (turn.session_id, turn.user_id, turn.role, turn.utterance, turn.timestamp, turn.enhanced_utterance))
            conn.commit()
            return cursor.lastrowid
        finally:
            self.pool.return_connection(conn)
    
    def get_turns_by_session(self, session_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, user_id, role, utterance, timestamp, enhanced_utterance
                FROM dialog_turns
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', (session_id, limit, offset))
            rows = cursor.fetchall()
            return [
                DialogTurn(
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    role=row['role'],
                    utterance=row['utterance'],
                    timestamp=row['timestamp'],
                    enhanced_utterance=row['enhanced_utterance']
                )
                for row in rows
            ]
        finally:
            self.pool.return_connection(conn)
    
    def get_turns_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, user_id, role, utterance, timestamp, enhanced_utterance
                FROM dialog_turns
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            rows = cursor.fetchall()
            return [
                DialogTurn(
                    session_id=row['session_id'],
                    user_id=row['user_id'],
                    role=row['role'],
                    utterance=row['utterance'],
                    timestamp=row['timestamp'],
                    enhanced_utterance=row['enhanced_utterance']
                )
                for row in rows
            ]
        finally:
            self.pool.return_connection(conn)
    
    def update_turns_user_id(self, session_id: str, old_user_id: str, new_user_id: str) -> bool:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE dialog_turns
                SET user_id = ?
                WHERE session_id = ? AND user_id = ?
            ''', (new_user_id, session_id, old_user_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self.pool.return_connection(conn)
    
    # ... 其他方法保持不变
```

#### 4.3 DialogStateManager 改进

```python
def get_or_create_dialog_state(self, session_id: str, user_id: str) -> DialogStateDTO:
    """获取或创建对话状态，必须传入 user_id"""
    # 从存储中获取对话状态
    state = self.dialog_repo.get_dialog_state(session_id)
    
    # 如果不存在，创建新的对话状态
    if not state:
        state = DialogStateDTO(
            session_id=session_id,
            user_id=user_id,  # 关联到用户
            current_intent=None,
            # ... 其他字段
        )
        self.dialog_repo.save_dialog_state(state)
    else:
        # 校验 user_id 一致性
        if state.user_id != user_id:
            # 可选择更新或抛出异常，根据业务需求
            state.user_id = user_id
            self.dialog_repo.update_dialog_state(state)
    
    return state
```

#### 4.4 交互处理改进

```python
def stream_handle_user_input(self, input: UserInputDTO):
    # 补全 user_id（如果为空）
    if not input.user_id:
        # 生成临时 user_id
        input.user_id = self._generate_temp_user_id(input.session_id)
    
    # 获取或创建对话状态
    dialog_state = self.dialog_state_manager.get_or_create_dialog_state(
        session_id=input.session_id,
        user_id=input.user_id
    )
    
    # 处理用户输入...
    
    # 保存用户输入到对话历史
    user_turn = DialogTurn(
        session_id=input.session_id,
        user_id=input.user_id,
        role="user",
        utterance=input.utterance
    )
    self.context_manager.add_turn(user_turn)
    
    # 生成系统响应...
    
    # 保存系统响应到对话历史
    system_turn = DialogTurn(
        session_id=input.session_id,
        user_id=input.user_id,
        role="system",
        utterance=response_text
    )
    self.context_manager.add_turn(system_turn)
    
    # 返回响应时包含 user_id
    yield "meta", {
        "session_id": response.session_id,
        "user_id": input.user_id,  # 新增
        "requires_input": ...,
        # ... 其他字段
    }
```

#### 4.5 临时 User ID 生成

```python
def _generate_temp_user_id(self, session_id: str) -> str:
    """生成临时 user_id"""
    import hashlib
    import time
    
    # 基于 session_id、时间戳和盐值生成
    salt = "flora_interaction_salt"
    hash_input = f"{session_id}_{time.time()}_{salt}"
    temp_user_id = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    return f"temp_{temp_user_id}"
```

### 5. 会话管理策略

#### 5.1 会话过期策略

- 设置会话 TTL：默认 30 分钟无活动自动过期
- 实现自动清理机制：定期清理过期会话
- 前端提示：会话即将过期时提示用户

#### 5.2 会话持久化

- 所有会话状态持久化到数据库
- 支持会话恢复：用户重新连接时可恢复之前的会话

#### 5.3 匿名用户处理

- 匿名用户自动分配临时 user_id
- 支持匿名用户转正式用户：通过 `bind-user` 接口
- 临时用户数据可选择保留或清理

### 6. 安全考虑

- **权限校验**：所有用户相关接口必须校验请求者身份
- **数据隔离**：不同用户的数据严格隔离
- **隐私保护**：敏感信息脱敏处理
- **日志安全**：日志中避免记录敏感信息

### 7. 监控与日志

- **日志增强**：所有日志必须包含 `user_id` 和 `session_id`
- **监控指标**：
  - 活跃用户数
  - 活跃会话数
  - 会话平均时长
  - 会话创建/销毁速率
- **异常检测**：监控异常会话行为，如频繁创建会话、异常访问模式等

## 四、实现步骤

1. **数据模型更新**：
   - 在 `DialogTurn` 中添加 `session_id` 和 `user_id` 字段
   - 在 `DialogStateDTO` 中添加 `user_id` 字段
   - 更新数据库表结构

2. **ContextManager 改进**：
   - 修改 `add_turn` 方法，支持带有 `session_id` 和 `user_id` 的 `DialogTurn`
   - 添加 `get_turns_by_session` 方法，根据会话ID获取对话轮次
   - 添加 `get_turns_by_user` 方法，根据用户ID获取对话轮次
   - 添加 `update_turn_user_id` 方法，用于匿名用户转正式用户

3. **DialogRepository 改进**：
   - 更新 `_create_table` 方法，添加 `session_id` 和 `user_id` 字段
   - 添加索引以提高查询性能
   - 更新 `save_turn` 方法，支持保存 `session_id` 和 `user_id`
   - 添加 `get_turns_by_session` 方法
   - 添加 `get_turns_by_user` 方法
   - 添加 `update_turns_user_id` 方法

4. **DialogStateManager 改进**：
   - 修改 `get_or_create_dialog_state` 方法，接收并使用 `user_id`
   - 实现 `user_id` 一致性校验

5. **交互处理改进**：
   - 补全 `user_id` 生成逻辑
   - 在响应中返回 `user_id`
   - 保存用户输入和系统响应到对话历史

6. **API 接口开发**：
   - 实现 `/api/v1/session/{session_id}` 接口
   - 实现 `/api/v1/user/{user_id}/sessions` 接口
   - 实现 `/api/v1/session/{session_id}/bind-user` 接口
   - 实现 `/api/v1/session/{session_id}/history` 接口
   - 实现 `/api/v1/user/{user_id}/history` 接口

7. **会话管理机制**：
   - 实现会话过期清理机制
   - 实现匿名用户处理逻辑
   - 实现对话历史管理策略

8. **测试与验证**：
   - 单元测试
   - 集成测试
   - 性能测试

9. **文档更新**：
   - 更新 API 文档
   - 更新开发文档
   - 更新数据库设计文档

## 五、预期效果

1. **清晰的用户-会话关系**：每个会话都关联到具体用户
2. **支持多设备同步**：同一用户在不同设备上的会话可管理
3. **灵活的用户类型**：支持匿名用户、临时用户和正式用户
4. **完善的查询接口**：前端可方便查询会话和用户信息
5. **可扩展的架构**：便于后续添加更多用户相关功能
6. **增强的安全性**：更好的权限控制和数据隔离

## 六、后续优化方向

1. **用户画像**：添加用户画像功能，支持个性化服务
2. **会话历史**：实现用户会话历史查询
3. **多设备同步**：支持用户在不同设备间同步会话
4. **会话迁移**：支持会话在不同设备间迁移
5. **用户行为分析**：基于用户会话数据进行行为分析

---

**设计人**：AI Assistant  
**设计日期**：2025-12-24  
**版本**：1.0