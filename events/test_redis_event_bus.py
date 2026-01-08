import asyncio
import json
from external.events.bus_impl_redis import RedisEventBus
from external.cache.redis_impl import redis_client

async def test_redis_event_bus():
    """测试Redis事件总线的发布和订阅功能"""
    print("=== 测试Redis事件总线开始 ===")
    
    # 创建事件总线实例
    event_bus = RedisEventBus(redis_client)
    topic = "test_topic"
    
    # 用于存储收到的消息
    received_messages = []
    
    async def subscriber():
        """订阅者协程"""
        print("订阅者已启动，等待消息...")
        async for message in event_bus.subscribe(topic):
            print(f"收到消息: {message}")
            received_messages.append(message)
            # 只接收一条消息就退出
            if len(received_messages) >= 1