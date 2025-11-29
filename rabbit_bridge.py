

# rabbit_bridge.py
import pika
import json
from thespian.actors import ActorSystem
import logging
from capability_actors.loop_scheduler_actor import LoopSchedulerActor
from config import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, RABBITMQ_VIRTUAL_HOST

def start_rabbit_bridge(thespian_system_name="multiprocTCPBase"):
    """
    RabbitMQ 桥接器：运行在独立线程中
    """
    bridge_logger = logging.getLogger("RabbitMQBridge")
    
    try:
        # 1. 获取 Actor 系统句柄
        asys = ActorSystem(thespian_system_name)
        
        def on_message(ch, method, properties, body):
            try:
                msg = json.loads(body)
                bridge_logger.info(f"收到 MQ 消息: {msg.get('task_id', 'unknown')}")
                
                # 获取 Scheduler 地址并转发
                scheduler_addr = asys.createActor(LoopSchedulerActor, globalName="loop_scheduler")
                asys.tell(scheduler_addr, {
                    "type": "rabbitmq_trigger",
                    **msg
                })
            except Exception as e:
                bridge_logger.error(f"消息处理错误: {e}")
            
            # 手动 ACK
            ch.basic_ack(delivery_tag=method.delivery_tag)

        # 2. 配置 RabbitMQ 连接参数 (使用你提供的配置)
        credentials = pika.PlainCredentials(RABBITMQ_USERNAME, RABBITMQ_PASSWORD)
        parameters = pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            virtual_host=RABBITMQ_VIRTUAL_HOST, # 注意这里用下划线
            credentials=credentials,
            heartbeat=60,            # 建议设置心跳防止连接断开
            blocked_connection_timeout=300
        )

        # 3. 建立连接
        bridge_logger.info(f"正在连接 RabbitMQ: {RABBITMQ_HOST}:{RABBITMQ_PORT}...")
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        
        # 声明队列 (确保队列存在，持久化)
        channel.queue_declare(queue='loop.trigger.queue', durable=True)
        
        channel.basic_consume(queue='loop.trigger.queue', on_message_callback=on_message)
        bridge_logger.info("RabbitMQ Bridge 连接成功，开始监听 loop.trigger.queue...")
        channel.start_consuming()
        
    except Exception as e:
        bridge_logger.error(f"RabbitMQ 连接失败: {e}")

