"""
Feedback Processor Service

Listens to feedback queue and uses LLM to refine filtering prompts.
"""
import os
import sys
import json
import requests

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, init_db
from shared.models import Task
from shared.mq_utils import consume_messages, publish_message


class FeedbackProcessor:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.api_url = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
        self.app_name = os.getenv("APP_NAME", "DynamicPipeline")

        if not self.api_key:
            print("Warning: OPENROUTER_API_KEY not set. Feedback processing will not work.")

    def refine_prompt(self, current_prompt: str, feedback: str) -> str:
        """
        Use LLM to generate an improved prompt based on feedback.
        """
        if not self.api_key:
            print("No API key configured")
            return current_prompt

        system_prompt = """You are a prompt engineer. Your task is to refine content filtering prompts based on user feedback.

You will be given:
1. The current filtering prompt
2. User feedback about the filtering results

Generate an improved version of the prompt that incorporates the user's feedback.
The improved prompt should:
- Maintain the same structure (asking for YES/NO decision)
- Include the feedback to make filtering more accurate
- Be clear and specific
- Keep the {{CONTENT}} placeholder

Return ONLY the improved prompt, nothing else."""

        user_message = f"""Current Prompt:
{current_prompt}

User Feedback:
{feedback}

Generate an improved prompt:"""

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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                improved_prompt = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

                if improved_prompt and len(improved_prompt) > 50:
                    return improved_prompt
                else:
                    print("LLM returned invalid prompt, keeping current one")
                    return current_prompt
            else:
                print(f"API error: {response.status_code} - {response.text}")
                return current_prompt

        except Exception as e:
            print(f"Error calling LLM: {e}")
            return current_prompt

    def process_message(self, ch, method, properties, body):
        """
        Process a feedback message.
        """
        try:
            data = json.loads(body)
            task_id = data.get("task_id")
            feedback = data.get("feedback")
            current_prompt = data.get("current_prompt")

            print(f"Processing feedback for task {task_id}...")

            # Refine prompt using LLM
            new_prompt = self.refine_prompt(current_prompt, feedback)

            # Update task in database
            with get_db() as db:
                task = db.query(Task).filter(Task.id == task_id).first()

                if task:
                    old_prompt = task.current_prompt
                    task.current_prompt = new_prompt
                    db.flush()

                    print(f"Updated prompt for task {task_id}")

                    # Send confirmation to user
                    publish_message("filtered_content_queue", {
                        "task_id": task_id,
                        "user_email": task.user_email,
                        "subject": f"Feedback Received - Task #{task_id}",
                        "body": f"""Thank you for your feedback!

Task ID: {task_id}

Your feedback has been processed and the filtering criteria have been updated.
Future content will be filtered using the refined criteria.

Original criteria focus:
{task.description}

You can continue to provide feedback on any notification to further improve the filtering.
"""
                    })
                else:
                    print(f"Task {task_id} not found")

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"Error processing feedback: {e}")
            # Reject and requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    def start(self):
        """Start consuming messages."""
        print("Feedback Processor started. Waiting for messages...")
        consume_messages("feedback_queue", self.process_message)


def main():
    # Initialize database
    print("Initializing database...")
    init_db()

    # Start feedback processor
    processor = FeedbackProcessor()
    processor.start()


if __name__ == "__main__":
    main()
