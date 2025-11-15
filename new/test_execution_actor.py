"""测试执行Actor"""
import sys
import os
from thespian.actors import ActorSystem

# 将项目根目录添加到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from new.capability_actors.execution_actor import ExecutionActor


def test_execution_actor():
    """测试执行Actor"""
    print("=== 测试执行Actor ===")
    
    # 创建Actor系统
    actor_system = ActorSystem('multiprocTCPBase')
    
    try:
        # 创建执行Actor
        execution_actor = actor_system.createActor(ExecutionActor)
        
        print(f"创建执行Actor成功, ID: {execution_actor}")
        
        # 检查Actor是否正常响应
        # 这里可以添加实际的消息测试
        
        print("=== 测试完成 ===")
        return True
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 关闭Actor系统
        actor_system.shutdown()


if __name__ == "__main__":
    success = test_execution_actor()
    sys.exit(0 if success else 1)