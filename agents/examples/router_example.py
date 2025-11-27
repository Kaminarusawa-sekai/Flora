"""
RouterActor引用管理机制示例

这个示例展示了如何使用新的中心化路由Actor和外部注册表机制来管理AgentActor的引用，
确保同一租户和节点下只有一个AgentActor实例。
"""

import logging
import time
from thespian.actors import ActorSystem
from ..router_actor import RouterActor, UserRequest
from ..agent_registry import AgentRegistry
from ..actor_reference_utils import actor_reference_utils

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RouterExample")


def run_example():
    """运行RouterActor引用管理示例"""
    logger.info("开始运行RouterActor引用管理示例")
    
    # 初始化Redis连接（如果可用）
    try:
        if actor_reference_utils.test_redis_connection():
            logger.info("Redis连接成功")
        else:
            logger.warning("Redis不可用，将使用内存作为备选存储")
    except Exception as e:
        logger.error(f"Redis连接测试失败: {e}")
    
    # 初始化ActorSystem
    logger.info("初始化ActorSystem...")
    actor_system = ActorSystem()
    
    try:
        # 创建RouterActor
        logger.info("创建RouterActor...")
        router_actor = actor_system.createActor(RouterActor)
        
        # 初始化AgentRegistry并配置RouterActor
        logger.info("初始化AgentRegistry并配置RouterActor...")
        agent_registry = AgentRegistry.get_instance()
        agent_registry.router_actor = router_actor
        agent_registry.actor_system = actor_system
        
        # 测试场景1: 使用get_or_create_agent_actor获取/创建AgentActor
        logger.info("测试场景1: 使用get_or_create_agent_actor")
        tenant_id = "test_tenant"
        node_id = "node_1"
        
        # 获取或创建AgentActor
        agent_actor_ref = agent_registry.get_or_create_agent_actor(tenant_id, node_id)
        
        if agent_actor_ref:
            logger.info(f"成功获取/创建AgentActor引用: tenant={tenant_id}, node={node_id}")
            
            # 测试发送消息
            test_message = {
                "message_type": "test_command",
                "content": "这是一条测试消息"
            }
            
            logger.info("向AgentActor发送测试消息...")
            agent_actor_ref(test_message)
            # 或者使用tell方法
            agent_actor_ref.tell(test_message)
            
            # 等待消息处理
            time.sleep(2)
        
        # 测试场景2: 使用agent_actor_context上下文管理器
        logger.info("测试场景2: 使用agent_actor_context上下文管理器")
        with agent_registry.agent_actor_context(tenant_id, node_id) as actor_ref:
            if actor_ref:
                logger.info("在上下文中使用AgentActor")
                actor_ref.tell({"message_type": "context_message", "content": "上下文管理器中的消息"})
                time.sleep(1)
        logger.info("上下文结束，资源应已清理")
        
        # 测试场景3: 检查唯一性保证
        logger.info("测试场景3: 检查唯一性保证")
        # 连续获取两次，应该返回同一个实例（或代理）
        actor_ref1 = agent_registry.get_or_create_agent_actor(tenant_id, node_id)
        actor_ref2 = agent_registry.get_or_create_agent_actor(tenant_id, node_id)
        
        # 注意：由于我们返回的是代理对象，这里比较的是代理对象的标识
        # 实际应用中，应该通过RouterActor检查Redis或内存存储来验证
        logger.info(f"获取的两个引用是否为同一对象: {actor_ref1 is actor_ref2}")
        
        # 测试场景4: 不同租户或节点的Actor创建
        logger.info("测试场景4: 创建不同租户/节点的AgentActor")
        other_tenant_actor = agent_registry.get_or_create_agent_actor("other_tenant", node_id)
        other_node_actor = agent_registry.get_or_create_agent_actor(tenant_id, "node_2")
        
        # 发送消息到其他Actor
        if other_tenant_actor:
            other_tenant_actor.tell({"message_type": "other_tenant_message"})
        if other_node_actor:
            other_node_actor.tell({"message_type": "other_node_message"})
        
        # 等待心跳机制和TTL刷新
        logger.info("等待心跳机制运行...")
        time.sleep(5)
        
        # 测试场景5: 检查Agent是否活跃
        logger.info("测试场景5: 检查Agent活跃度")
        agent_id = f"{tenant_id}_{node_id}"
        is_active = agent_registry.is_agent_active(agent_id)
        logger.info(f"Agent {agent_id} 是否活跃: {is_active}")
        
        logger.info("示例运行完成")
        
    except Exception as e:
        logger.error(f"示例运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        logger.info("清理ActorSystem资源...")
        actor_system.shutdown()


def main():
    """主函数"""
    run_example()


if __name__ == "__main__":
    main()
