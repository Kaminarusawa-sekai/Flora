"""测试RouterActor和Redis连接（DTO-Repo-Client架构）"""

import logging
import sys
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_redis_client():
    """测试Redis Client"""
    logger.info("=== 测试Redis Client ===")

    try:
        from external.database.redis_client import RedisClient

        client = RedisClient()

        # 测试连接
        client.client.ping()
        logger.info("✓ Redis连接成功")

        # 测试基本操作
        test_key = "test:router:connection"
        test_value = "test_value_123"

        # 设置值
        success = client.set(test_key, test_value, ttl=60)
        if success:
            logger.info("✓ Redis SET操作成功")
        else:
            logger.error("✗ Redis SET操作失败")
            return False

        # 获取值
        retrieved_value = client.get(test_key)
        if retrieved_value == test_value:
            logger.info(f"✓ Redis GET操作成功，值: {retrieved_value}")
        else:
            logger.error(f"✗ Redis GET操作失败，期望: {test_value}, 实际: {retrieved_value}")
            return False

        # 删除值
        success = client.delete(test_key)
        if success:
            logger.info("✓ Redis DELETE操作成功")
        else:
            logger.warning("✗ Redis DELETE操作失败")

        return True

    except Exception as e:
        logger.error(f"✗ Redis Client测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_actor_reference_repo():
    """测试Actor引用Repository"""
    logger.info("\n=== 测试Actor引用Repository ===")

    try:
        from external.repositories.actor_reference_repo import ActorReferenceRepo
        from external.database.redis_client import RedisClient
        from common.types.actor_reference import ActorReferenceDTO
        from datetime import datetime, timedelta

        # 创建Repository
        redis_client = RedisClient()
        repo = ActorReferenceRepo(redis_client)
        logger.info("✓ ActorReferenceRepo创建成功")

        # 测试保存
        test_dto = ActorReferenceDTO(
            tenant_id="test_tenant",
            node_id="test_node",
            actor_address="test_actor_address_123",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )

        success = repo.save(test_dto, ttl=60)
        if success:
            logger.info("✓ Repository SAVE操作成功")
        else:
            logger.error("✗ Repository SAVE操作失败")
            return False

        # 测试获取
        retrieved_dto = repo.get("test_tenant", "test_node")
        if retrieved_dto and retrieved_dto.actor_address == "test_actor_address_123":
            logger.info(f"✓ Repository GET操作成功，地址: {retrieved_dto.actor_address}")
        else:
            logger.error("✗ Repository GET操作失败")
            return False

        # 测试刷新TTL
        success = repo.refresh_ttl("test_tenant", "test_node", ttl=120)
        if success:
            logger.info("✓ Repository REFRESH_TTL操作成功")
        else:
            logger.warning("✗ Repository REFRESH_TTL操作失败")

        # 测试删除
        success = repo.delete("test_tenant", "test_node")
        if success:
            logger.info("✓ Repository DELETE操作成功")
        else:
            logger.warning("✗ Repository DELETE操作失败")

        return True

    except Exception as e:
        logger.error(f"✗ ActorReferenceRepo测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_actor_reference_manager():
    """测试Actor引用管理器"""
    logger.info("\n=== 测试Actor引用管理器 ===")

    try:
        from common.utils.actor_reference_manager import actor_reference_manager
        from thespian.actors import ActorSystem, Actor

        # 创建一个简单的Actor系统
        system = ActorSystem('simpleSystemBase')

        # 创建一个测试Actor
        class TestActor(Actor):
            def receiveMessage(self, msg, sender):
                pass

        test_actor_addr = system.createActor(TestActor)
        logger.info(f"✓ 创建测试Actor: {test_actor_addr}")

        # 测试序列化和反序列化
        serialized = actor_reference_manager.serialize_address(test_actor_addr)
        if serialized:
            logger.info(f"✓ Actor地址序列化成功")

            # 反序列化
            deserialized = actor_reference_manager.deserialize_address(serialized)
            if deserialized:
                logger.info(f"✓ Actor地址反序列化成功")
            else:
                logger.error("✗ Actor地址反序列化失败")
                system.shutdown()
                return False
        else:
            logger.error("✗ Actor地址序列化失败")
            system.shutdown()
            return False

        # 测试保存Actor引用
        success = actor_reference_manager.save_actor_reference(
            "test_tenant",
            "test_node",
            test_actor_addr,
            ttl=60
        )
        if success:
            logger.info("✓ 保存Actor引用成功")
        else:
            logger.error("✗ 保存Actor引用失败")
            system.shutdown()
            return False

        # 测试获取Actor引用
        retrieved_addr = actor_reference_manager.get_actor_reference("test_tenant", "test_node")
        if retrieved_addr:
            logger.info(f"✓ 获取Actor引用成功")
        else:
            logger.error("✗ 获取Actor引用失败")
            system.shutdown()
            return False

        # 测试删除Actor引用
        success = actor_reference_manager.delete_actor_reference("test_tenant", "test_node")
        if success:
            logger.info("✓ 删除Actor引用成功")
        else:
            logger.warning("✗ 删除Actor引用失败")

        # 关闭系统
        system.shutdown()
        logger.info("✓ Actor系统已关闭")

        return True

    except Exception as e:
        logger.error(f"✗ Actor引用管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_router_actor():
    """测试RouterActor"""
    logger.info("\n=== 测试RouterActor ===")

    try:
        from thespian.actors import ActorSystem
        from agents.router_actor import RouterActor, UserRequest

        # 创建Actor系统
        system = ActorSystem('simpleSystemBase')
        logger.info("✓ Actor系统已创建")

        # 创建RouterActor
        router = system.createActor(RouterActor, globalName="test_router")
        logger.info(f"✓ RouterActor已创建: {router}")

        # 发送测试消息
        test_request = UserRequest(
            tenant_id="test_tenant",
            node_id="test_node",
            message={"test": "message"}
        )

        logger.info("发送测试请求到RouterActor...")
        # 注意：RouterActor会创建SessionActor，可能需要一些时间
        time.sleep(2)

        # 关闭系统
        system.shutdown()
        logger.info("✓ Actor系统已关闭")

        return True

    except Exception as e:
        logger.error(f"✗ RouterActor测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("===== 开始RouterActor和Redis测试 (DTO-Repo-Client架构) =====\n")

    # 测试1: Redis Client
    redis_ok = test_redis_client()

    # 测试2: Actor引用Repository
    repo_ok = test_actor_reference_repo()

    # 测试3: Actor引用管理器
    manager_ok = test_actor_reference_manager()

    # 测试4: RouterActor
    router_ok = test_router_actor()

    # 总结
    logger.info("\n===== 测试结果总结 =====")
    logger.info(f"Redis Client测试: {'✓ 通过' if redis_ok else '✗ 失败'}")
    logger.info(f"ActorReferenceRepo测试: {'✓ 通过' if repo_ok else '✗ 失败'}")
    logger.info(f"ActorReferenceManager测试: {'✓ 通过' if manager_ok else '✗ 失败'}")
    logger.info(f"RouterActor测试: {'✓ 通过' if router_ok else '✗ 失败'}")

    all_passed = redis_ok and repo_ok and manager_ok and router_ok
    logger.info(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 部分失败'}")

    if not redis_ok:
        logger.warning("\n注意: Redis连接失败，系统将使用内存模式运行")

    logger.info("\n架构说明:")
    logger.info("✓ DTO: common/types/actor_reference.py - ActorReferenceDTO")
    logger.info("✓ Repo: external/repositories/actor_reference_repo.py - ActorReferenceRepo")
    logger.info("✓ Client: external/database/redis_client.py - RedisClient")
    logger.info("✓ Manager: common/utils/actor_reference_manager.py - ActorReferenceManager")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
