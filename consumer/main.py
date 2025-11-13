"""
Consumer Service

Listens to raw content queue and filters using LLM via OpenRouter API.
"""
import os
import sys
import json
import requests
from typing import Dict, Any

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, init_db
from shared.models import Task
from shared.mq_utils import consume_messages, publish_message


class Consumer:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.api_url = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.app_name = os.getenv("APP_NAME", "DynamicPipeline")

        if not self.api_key:
            print("Warning: OPENROUTER_API_KEY not set. LLM filtering will not work.")

    def call_llm(self, prompt: str, content: str) -> str:
        """
        Call OpenRouter API to filter content.

        Returns: "YES", "NO", or "ERROR"
        """
        if not self.api_key:
            print("No API key configured")
            return "ERROR"

        # Replace placeholder in prompt with actual content
        full_prompt = prompt.replace("{{CONTENT}}", content)

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/yourusername/dynamic-pipeline",
                "X-Title": self.app_name
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()

                # Normalize answer
                if "YES" in answer:
                    return "YES"
                elif "NO" in answer:
                    return "NO"
                else:
                    return answer[:10]  # Return first 10 chars if unclear
            else:
                print(f"API error: {response.status_code} - {response.text}")
                return "ERROR"

        except Exception as e:
            print(f"Error calling LLM: {e}")
            return "ERROR"

    def process_message(self, ch, method, properties, body):
        """
        Process a message from the raw content queue.
        """
        try:
            data = json.loads(body)
            task_id = data.get("task_id")
            item = data.get("item")
            content = data.get("content")

            print(f"Processing content for task {task_id}...")

            # Get task from database
            with get_db() as db:
                task = db.query(Task).filter(Task.id == task_id).first()

                if not task:
                    print(f"Task {task_id} not found")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                if task.status != "active":
                    print(f"Task {task_id} is not active (status: {task.status})")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                # Call LLM to filter
                decision = self.call_llm(task.current_prompt, content)

                print(f"LLM decision for task {task_id}: {decision}")

                if decision == "YES":
                    # Content is relevant, send to notifier
                    subject = self.generate_subject(task, item)
                    body_text = self.generate_body(task, item, content)

                    publish_message("filtered_content_queue", {
                        "task_id": task_id,
                        "user_email": task.user_email,
                        "subject": subject,
                        "body": body_text
                    })

                    print(f"Published relevant content for task {task_id}")

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"Error processing message: {e}")
            # Reject and requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def generate_subject(self, task: Task, item: dict) -> str:
        """Generate email subject for notification."""
        title = item.get("title", "New Content")
        return f"[Task #{task.id}] {title[:50]}"

    def generate_body(self, task: Task, item: dict, content: str) -> str:
        """Generate email body for notification."""
        body = f"""New relevant content found for your monitoring task!

Task ID: {task.id}
Task Description: {task.description}

{"-" * 60}

{content}

{"-" * 60}

Reply to this email with feedback to improve filtering:
- "This is exactly what I want" - to reinforce this type of content
- "This is not relevant" - to filter out similar content
- Any other feedback to refine the criteria
"""
        return body

    def start(self):
        """Start consuming messages."""
        print("Consumer started. Waiting for messages...")
        consume_messages("raw_content_queue", self.process_message)


def main():
    # Initialize database
    print("Initializing database...")
    init_db()

    # Start consumer
    consumer = Consumer()
    consumer.start()


if __name__ == "__main__":
    main()
