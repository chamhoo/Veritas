import os
import sys
import json

# Add shared module to path
sys.path.insert(0, '/root/Veritas')

from dotenv import load_dotenv
from openai import OpenAI

from shared.database import get_session, init_db
from shared.models import Task
from shared.mq_utils import consume_messages, FEEDBACK_QUEUE

load_dotenv()

# OpenRouter client
client = OpenAI(
    base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
    api_key=os.getenv('OPENROUTER_API_KEY')
)

def generate_improved_prompt(current_prompt, feedback):
    """
    Use LLM to generate an improved prompt based on user feedback.

    Args:
        current_prompt: The current filtering prompt
        feedback: User's feedback text

    Returns:
        str: The improved prompt
    """
    try:
        response = client.chat.completions.create(
            model=os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
            messages=[
                {
                    "role": "system",
                    "content": """You are a prompt engineer specializing in content filtering.
                    Your task is to improve a filtering prompt based on user feedback.

                    Guidelines:
                    1. Preserve the core intent of the original prompt
                    2. Incorporate the user's feedback to refine the criteria
                    3. Make the prompt more specific to avoid unwanted matches
                    4. Keep the prompt clear and actionable
                    5. Output ONLY the improved prompt text, nothing else

                    Examples of feedback interpretation:
                    - "this is irrelevant" -> add exclusion criteria for similar content
                    - "show me more like this" -> strengthen criteria that matched this content
                    - "focus more on X" -> increase weight/emphasis on X in the prompt
                    - "ignore posts about Y" -> add explicit exclusion for Y
                    """
                },
                {
                    "role": "user",
                    "content": f"""Current filtering prompt:
{current_prompt}

User feedback:
{feedback}

Generate an improved prompt that incorporates this feedback."""
                }
            ],
            max_tokens=500
        )

        improved_prompt = response.choices[0].message.content.strip()

        # Remove any markdown formatting if present
        if improved_prompt.startswith('```'):
            lines = improved_prompt.split('\n')
            improved_prompt = '\n'.join(lines[1:-1])

        return improved_prompt

    except Exception as e:
        print(f"Error generating improved prompt: {e}")
        return None

def update_task_prompt(task_id, new_prompt):
    """Update the task's current prompt in the database."""
    session = get_session()
    try:
        task = session.query(Task).filter(Task.id == task_id).first()

        if not task:
            print(f"Task {task_id} not found")
            return False

        task.current_prompt = new_prompt
        session.commit()

        print(f"Updated prompt for task {task_id}")
        return True

    except Exception as e:
        session.rollback()
        print(f"Error updating task prompt: {e}")
        return False
    finally:
        session.close()

def process_feedback(ch, method, properties, body):
    """Process feedback message and update task prompt."""
    try:
        message = json.loads(body)

        task_id = message.get('task_id')
        user_email = message.get('user_email')
        feedback = message.get('feedback')
        current_prompt = message.get('current_prompt')

        print(f"Processing feedback for task {task_id} from {user_email}")
        print(f"Feedback: {feedback[:100]}...")

        # Generate improved prompt
        improved_prompt = generate_improved_prompt(current_prompt, feedback)

        if improved_prompt:
            # Update the task in database
            success = update_task_prompt(task_id, improved_prompt)

            if success:
                print(f"Successfully updated prompt for task {task_id}")
                print(f"New prompt: {improved_prompt[:200]}...")
            else:
                print(f"Failed to update prompt for task {task_id}")
        else:
            print(f"Failed to generate improved prompt for task {task_id}")

        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except json.JSONDecodeError as e:
        print(f"Error decoding message: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing feedback: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    """Main function to run the feedback processor service."""
    print("Starting Feedback Processor Service...")

    # Initialize database
    init_db()

    print("Listening for messages on feedback_queue...")

    # Start consuming messages
    consume_messages(FEEDBACK_QUEUE, process_feedback)

if __name__ == '__main__':
    main()
