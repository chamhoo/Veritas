import os
import json
import pika
from functools import wraps
from typing import Dict, Any, Callable

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")

def connect_to_rabbitmq():
    """Create a connection to RabbitMQ"""
    try:
        parameters = pika.URLParameters(RABBITMQ_URL)
        connection = pika.BlockingConnection(parameters)
        return connection
    except Exception as e:
        print(f"Failed to connect to RabbitMQ: {e}")
        raise

def setup_channel(queue_name: str):
    """Setup a channel with the specified queue"""
    connection = connect_to_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    return connection, channel

def publish_message(queue_name: str, message: Dict[str, Any]):
    """Publish a message to the specified queue"""
    connection, channel = setup_channel(queue_name)
    try:
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
    finally:
        connection.close()

def consume_queue(queue_name: str, callback: Callable):
    """Consume messages from the specified queue"""
    connection, channel = setup_channel(queue_name)
    
    @wraps(callback)
    def wrapped_callback(ch, method, properties, body):
        try:
            message = json.loads(body)
            callback(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=wrapped_callback)
    
    print(f"Started consuming from {queue_name}")
    channel.start_consuming()
