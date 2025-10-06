import os
import json
import pika
from typing import Dict, Any, Callable

class RabbitMQClient:
    """
    Client for interacting with RabbitMQ message queues.
    """
    def __init__(self, rabbitmq_url=None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL")
        self.connection = None
        self.channel = None
        
    def connect(self):
        """Establish connection to RabbitMQ."""
        self.connection = pika.BlockingConnection(
            pika.URLParameters(self.rabbitmq_url)
        )
        self.channel = self.connection.channel()
        
    def close(self):
        """Close the connection."""
        if self.connection and self.connection.is_open:
            self.connection.close()
    
    def declare_queue(self, queue_name: str):
        """Declare a queue if it doesn't exist."""
        if not self.channel:
            self.connect()
        self.channel.queue_declare(queue=queue_name, durable=True)
    
    def publish(self, queue_name: str, message: Dict[str, Any]):
        """Publish a message to the specified queue."""
        if not self.channel:
            self.connect()
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            )
        )
    
    def consume(self, queue_name: str, callback: Callable):
        """
        Start consuming messages from the specified queue.
        The callback function receives the decoded JSON message.
        """
        if not self.channel:
            self.connect()
            
        def wrapper(ch, method, properties, body):
            message = json.loads(body)
            callback(message)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=wrapper
        )
        self.channel.start_consuming()
