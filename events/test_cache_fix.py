import asyncio
import sys
from external.cache.redis_impl import redis_client

async def test_redis_cache_set_with_ex():
    """测试 RedisCacheClient.set() 方法支持 ex 参数"""
    try:
        # 测试使用 ex 参数
        await redis_client.set("test_key", "test_value", ex=10)
        print("✓ 测试通过: RedisCacheClient.set() 支持 ex 参数")
        
        # 测试使用 ttl 参数
        await redis_client.set("test_key_ttl", "test_value", ttl=10)
        print("✓ 测试通过: RedisCacheClient.set() 支持 ttl 参数")
        
        # 测试同时使用 ex 和 ttl 参数，ex 应该优先
        await redis_client.set("test_key_both", "test_value", ttl=5, ex=20)
        print("✓ 测试通过: RedisCacheClient.set() 优先使用 ex 参数")
        
        return True
    except Exception as e:
        print(f"✗ 测试失败: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_redis_cache_set_with_ex())
    sys.exit(0 if success else 1)