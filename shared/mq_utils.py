import os
import json
import pika
import time
import logging
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class RabbitMQClient:
    """
    Client for interacting with RabbitMQ message queues.
    """
    def __init__(self, rabbitmq_url=None, max_retries=5, retry_delay=5):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL")
        self.connection = None
        self.channel = None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def connect(self):
        """Establish connection to RabbitMQ with retry logic."""
        retries = 0
        while retries < self.max_retries:
            try:
                self.connection = pika.BlockingConnection(
                    pika.URLParameters(self.rabbitmq_url)
                )
                self.channel = self.connection.channel()
                logger.info("Successfully connected to RabbitMQ")
                return
            except Exception as e:
                retries += 1
                logger.warning(f"Failed to connect to RabbitMQ (attempt {retries}/{self.max_retries}): {e}")
                if retries < self.max_retries:
                    time.sleep(self.retry_delay)
                else:
                    logger.error("Could not connect to RabbitMQ after maximum retries")
                    raise
        
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
        """Publish a message to the specified queue with retry logic."""
        retries = 0
        while retries < 3:
            try:
                if not self.channel or self.channel.is_closed:
                    self.connect()
                self.channel.basic_publish(
                    exchange='',
                    routing_key=queue_name,
                    body=json.dumps(message),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # make message persistent
                    )
                )
                return
            except Exception as e:
                retries += 1
                logger.warning(f"Failed to publish message (attempt {retries}/3): {e}")
                if retries < 3:
                    time.sleep(2)
                    try:
                        self.connect()
                    except:
                        pass
                else:
                    logger.error(f"Could not publish message after 3 attempts: {e}")
                    raise
    
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
