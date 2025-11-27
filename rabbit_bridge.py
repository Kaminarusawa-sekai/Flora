

# rabbit_bridge.py
import pika
import json
from thespian.actors import ActorSystem

def start_rabbit_bridge(thespian_system_name="multiprocTCPBase"):
    asys = ActorSystem(thespian_system_name)

    def on_message(ch, method, properties, body):
        try:
            msg = json.loads(body)
            # 发送给全局 LoopSchedulerActor
            scheduler_addr = asys.createActor(None, globalName="loop_scheduler")
            asys.tell(scheduler_addr, {
                "type": "rabbitmq_trigger",
                **msg
            })
        except Exception as e:
            print(f"Bridge error: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    connection = pika.BlockingConnection(pika.URLParameters("amqp://guest:guest@localhost:5672/"))
    channel = connection.channel()
    channel.basic_consume(queue='loop.trigger.queue', on_message_callback=on_message)
    print("RabbitMQ bridge started...")
    channel.start_consuming()