"""
RabbitMQ utility functions for message queue operations.
"""
import os
import json
import pika
import time
from typing import Dict, Any, Callable
from contextlib import contextmanager


def get_rabbitmq_connection():
    """
    Create and return a RabbitMQ connection with retry logic.
    """
    rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
    rabbitmq_pass = os.getenv("RABBITMQ_PASS", "guest")

    max_retries = 5
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
            parameters = pika.ConnectionParameters(
                host=rabbitmq_host,
                port=rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            connection = pika.BlockingConnection(parameters)
            return connection
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Failed to connect to RabbitMQ (attempt {attempt + 1}/{max_retries}): {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Could not connect to RabbitMQ after {max_retries} attempts") from e


@contextmanager
def get_channel():
    """
    Context manager for RabbitMQ channel operations.
    """
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    try:
        yield channel
    finally:
        connection.close()


def publish_message(queue_name: str, message: Dict[Any, Any]):
    """
    Publish a message to a specific queue.

    Args:
        queue_name: Name of the queue
        message: Dictionary to be sent as JSON
    """
    with get_channel() as channel:
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
            )
        )


def consume_messages(queue_name: str, callback: Callable):
    """
    Start consuming messages from a queue with auto-reconnect.

    Args:
        queue_name: Name of the queue
        callback: Function to call for each message (should accept ch, method, properties, body)
    """
    while True:
        try:
            connection = get_rabbitmq_connection()
            channel = connection.channel()
            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)

            print(f"Started consuming from queue: {queue_name}")
            channel.start_consuming()
        except KeyboardInterrupt:
            print("Stopping consumer...")
            break
        except Exception as e:
            print(f"Connection lost: {e}")
            print("Reconnecting in 5 seconds...")
            time.sleep(5)
