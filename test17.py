import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('amqp://admin:Lanba%40123@121.36.203.36:10005/prod'))
channel = connection.channel()

# 设置为自动确认模式（用于测试）
method, properties, body = channel.basic_get(queue='task.result', auto_ack=True)

if method:
    print("Message body:", body.decode('utf-8'))
else:
    print("No message available")

connection.close()