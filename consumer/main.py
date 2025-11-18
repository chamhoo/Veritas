import os
import sys
import json

# Add shared module to path
sys.path.insert(0, '/root/Veritas')

from dotenv import load_dotenv
from openai import OpenAI

from shared.database import get_session, init_db
from shared.models import Task
from shared.mq_utils import consume_messages, publish_message, RAW_CONTENT_QUEUE, FILTERED_CONTENT_QUEUE

load_dotenv()

# OpenRouter client
client = OpenAI(
    base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
    api_key=os.getenv('OPENROUTER_API_KEY')
)

def get_task_prompt(task_id):
    """Retrieve the current prompt for a task from the database."""
    session = get_session()
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            return task.current_prompt
        return None
    finally:
        session.close()

def filter_content(content, prompt):
    """
    Use LLM to determine if content matches the filtering criteria.

    Returns:
        tuple: (is_relevant: bool, reason: str)
    """
    # Build content string
    content_text = f"""
Title: {content.get('title', 'No Title')}

Content: {content.get('content', 'No Content')[:2000]}

URL: {content.get('url', 'No URL')}

Author: {content.get('author', 'Unknown')}
"""

    try:
        response = client.chat.completions.create(
            model=os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
            messages=[
                {
                    "role": "system",
                    "content": """You are a content filter. Given filtering criteria and content,
                    determine if the content is relevant.

                    Respond with ONLY a JSON object in this exact format:
                    {"relevant": true/false, "reason": "brief explanation"}

                    Be strict but fair. Only mark as relevant if it truly matches the criteria.
                    """
                },
                {
                    "role": "user",
                    "content": f"""Filtering Criteria:
{prompt}

Content to evaluate:
{content_text}

Is this content relevant? Respond with JSON only."""
                }
            ],
            max_tokens=200
        )

        response_text = response.choices[0].message.content.strip()

        # Parse JSON response
        # Handle potential markdown code blocks
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]

        result = json.loads(response_text)
        return result.get('relevant', False), result.get('reason', 'No reason provided')

    except json.JSONDecodeError as e:
        print(f"Error parsing LLM response: {e}")
        # Default to not relevant if we can't parse
        return False, "Error parsing response"
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return False, str(e)

def format_notification(item, source_type, source_identifier, task_id, reason):
    """Format content into a user-friendly notification email."""
    subject = f"[Task {task_id}] {item.get('title', 'New Content')[:100]}"

    body = f"""New relevant content found for your monitoring task!

Task ID: {task_id}
Source: {source_type}:{source_identifier}

---

Title: {item.get('title', 'No Title')}

{item.get('content', 'No content available')[:1500]}

---

Link: {item.get('url', 'No URL available')}
Author: {item.get('author', 'Unknown')}

---

Why this was matched: {reason}

---

To provide feedback on this notification, simply reply to this email with your comments.
For example:
- "This is not relevant, ignore posts about X"
- "Good match! Show me more like this"
- "Focus more on Y instead"

Your feedback will help improve future filtering.
"""

    return subject, body

def process_message(ch, method, properties, body):
    """Process a message from the raw content queue."""
    try:
        message = json.loads(body)

        task_id = message.get('task_id')
        user_email = message.get('user_email')
        item = message.get('item', {})
        source_type = message.get('source_type')
        source_identifier = message.get('source_identifier')

        print(f"Processing content for task {task_id}: {item.get('title', 'Unknown')[:50]}")

        # Get the current prompt for this task
        prompt = get_task_prompt(task_id)

        if not prompt:
            print(f"No prompt found for task {task_id}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Filter the content
        is_relevant, reason = filter_content(item, prompt)

        if is_relevant:
            print(f"Content is relevant: {reason}")

            # Format notification
            subject, email_body = format_notification(
                item, source_type, source_identifier, task_id, reason
            )

            # Publish to filtered content queue
            notification = {
                'task_id': task_id,
                'user_email': user_email,
                'subject': subject,
                'body': email_body,
                'item_url': item.get('url', '')
            }

            publish_message(FILTERED_CONTENT_QUEUE, notification)
            print(f"Notification queued for task {task_id}")
        else:
            print(f"Content filtered out: {reason}")

        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error processing message: {e}")
        # Reject and requeue on error
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    """Main function to run the consumer service."""
    print("Starting Consumer (Filter) Service...")

    # Initialize database
    init_db()

    print("Listening for messages on raw_content_queue...")

    # Start consuming messages
    consume_messages(RAW_CONTENT_QUEUE, process_message)

if __name__ == '__main__':
    main()
