import os
import time
import json
import pika

# Queue names
RAW_CONTENT_QUEUE = 'raw_content_queue'
FILTERED_CONTENT_QUEUE = 'filtered_content_queue'
FEEDBACK_QUEUE = 'feedback_queue'

def get_rabbitmq_connection(max_retries=5, retry_delay=5):
    """Create and return a RabbitMQ connection with retry logic."""
    host = os.getenv('RABBITMQ_HOST', 'localhost')
    port = int(os.getenv('RABBITMQ_PORT', '5672'))
    user = os.getenv('RABBITMQ_USER', 'guest')
    password = os.getenv('RABBITMQ_PASSWORD', 'guest')

    credentials = pika.PlainCredentials(user, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )

    for attempt in range(max_retries):
        try:
            connection = pika.BlockingConnection(parameters)
            return connection
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"RabbitMQ connection attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed to connect to RabbitMQ after {max_retries} attempts: {e}")

def declare_queues(channel):
    """Declare all required queues."""
    channel.queue_declare(queue=RAW_CONTENT_QUEUE, durable=True)
    channel.queue_declare(queue=FILTERED_CONTENT_QUEUE, durable=True)
    channel.queue_declare(queue=FEEDBACK_QUEUE, durable=True)

def publish_message(queue_name, message):
    """Publish a message to the specified queue."""
    connection = get_rabbitmq_connection()
    try:
        channel = connection.channel()
        declare_queues(channel)

        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )
    finally:
        connection.close()

def consume_messages(queue_name, callback):
    """
    Consume messages from the specified queue.

    Args:
        queue_name: Name of the queue to consume from
        callback: Function to call for each message. Should accept (channel, method, properties, body)
    """
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    declare_queues(channel)

    # Set prefetch to 1 for fair dispatch
    channel.basic_qos(prefetch_count=1)

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback
    )

    print(f"Waiting for messages on {queue_name}. To exit press CTRL+C")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()
