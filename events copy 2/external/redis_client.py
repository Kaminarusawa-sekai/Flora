import os

# 尝试导入redis，若缺失则提供优雅的错误处理
try:
    import redis.asyncio as redis
    HAS_REDIS = True
    
    # Redis连接配置
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # 创建Redis客户端实例
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except ImportError:
    HAS_REDIS = False
    redis = None
    redis_client = None

async def set_cancel_signal(trace_id: str) -> bool:
    """
    设置取消信号
    
    Args:
        trace_id: 跟踪ID
        
    Returns:
        bool: 设置结果
    """
    if HAS_REDIS and redis_client:
        result = await redis_client.hset(f"cmd:instance:{trace_id}", "global_action", "CANCEL")
        return result > 0
    return False

async def set_pause_signal(trace_id: str, reason: str = "") -> bool:
    """
    设置暂停信号
    
    Args:
        trace_id: 跟踪ID
        reason: 暂停原因
        
    Returns:
        bool: 设置结果
    """
    if HAS_REDIS and redis_client:
        result = await redis_client.hset(f"cmd:instance:{trace_id}", "global_action", "PAUSE")
        if reason:
            await redis_client.hset(f"cmd:instance:{trace_id}", "pause_reason", reason)
        return result > 0
    return False

async def clear_signal(trace_id: str) -> bool:
    """
    清除信号
    
    Args:
        trace_id: 跟踪ID
        
    Returns:
        bool: 清除结果
    """
    if HAS_REDIS and redis_client:
        result = await redis_client.delete(f"cmd:instance:{trace_id}")
        return result > 0
    return False

async def check_cancelled(trace_id: str) -> bool:
    """
    Agent检查是否被取消
    
    Args:
        trace_id: 跟踪ID
        
    Returns:
        bool: 是否被取消
    """
    if HAS_REDIS and redis_client:
        action = await redis_client.hget(f"cmd:instance:{trace_id}", "global_action")
        return action == "CANCEL"
    return False

async def check_paused(trace_id: str) -> bool:
    """
    Agent检查是否被暂停
    
    Args:
        trace_id: 跟踪ID
        
    Returns:
        bool: 是否被暂停
    """
    if HAS_REDIS and redis_client:
        action = await redis_client.hget(f"cmd:instance:{trace_id}", "global_action")
        return action == "PAUSE"
    return False

async def get_signal(trace_id: str) -> str:
    """
    获取当前信号
    
    Args:
        trace_id: 跟踪ID
        
    Returns:
        str: 当前信号值
    """
    if HAS_REDIS and redis_client:
        return await redis_client.hget(f"cmd:instance:{trace_id}", "global_action")
    return None
