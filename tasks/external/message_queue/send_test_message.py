#!/usr/bin/env python3
import pika
import json
import sys

# 真实的RabbitMQ地址
RABBITMQ_URL = ""
QUEUE_NAME = "worker.execute"

def send_test_message():
    """向RabbitMQ发送测试消息"""
    try:
        # 连接到RabbitMQ服务器
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        
        # 声明exchange和queue（与监听器保持一致）
        channel.exchange_declare(
            exchange=QUEUE_NAME,
            exchange_type='direct',
            durable=True
        )
        
        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True
        )
        
        channel.queue_bind(
            queue=QUEUE_NAME,
            exchange=QUEUE_NAME,
            routing_key=QUEUE_NAME
        )
        
        # 准备测试消息
        test_message = {
            "msg_type": "START_TASK",
            "instance_id": "test-instance-99",
            "definition_id": "test-definition-888",
            "trace_id": "test-trace-777",
            "input_params": {
                "test_key": "test_value",
                "message": "这是一条测试消息"
            },
            "user_id": "test-sender"
        }
        
        # 发送消息
        channel.basic_publish(
            exchange=QUEUE_NAME,
            routing_key=QUEUE_NAME,
            body=json.dumps(test_message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 使消息持久化
            )
        )
        
        print(f"✓ 测试消息已发送到队列 '{QUEUE_NAME}'")
        print(f"✓ 消息内容: {json.dumps(test_message, indent=2)}")
        
        # 关闭连接
        connection.close()
        
    except Exception as e:
        print(f"✗ 发送消息失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"开始向RabbitMQ发送测试消息...")
    print(f"RabbitMQ URL: {RABBITMQ_URL}")
    print(f"目标队列: {QUEUE_NAME}")
    print()
    
    send_test_message()
    
    print()
    print("消息发送完成！请检查您的RabbitMQ监听器是否收到了消息。")
