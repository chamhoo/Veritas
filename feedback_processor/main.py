import os
import requests
from sqlalchemy.orm import Session
import sys
sys.path.append('/app')

from shared.database import get_db
from shared.models import Task
from shared.mq_utils import consume_queue

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")

def generate_improved_prompt(current_prompt, feedback_text):
    """Generate an improved prompt using the LLM based on feedback"""
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set")
        return current_prompt

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Prepare the message to generate an improved prompt
    message_content = f"""
    You are helping to improve a content filtering system. The system uses a prompt to determine if content is relevant to a user's interests.

    CURRENT PROMPT:
    ```
    {current_prompt}
    ```

    USER FEEDBACK:
    ```
    {feedback_text}
    ```

    Please generate an improved version of the prompt that incorporates the user's feedback. The prompt should still follow the same basic structure but be more accurate based on the feedback.
    
    Return ONLY the improved prompt, nothing else.
    """

    data = {
        "model": "openai/gpt-4",  # Using GPT-4 for this meta-level task
        "messages": [
            {"role": "system", "content": "You are an expert prompt engineer helping to improve content filtering."},
            {"role": "user", "content": message_content}
        ]
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        new_prompt = result['choices'][0]['message']['content'].strip()
        
        print("Generated improved prompt")
        return new_prompt
    except Exception as e:
        print(f"Error calling LLM API for prompt improvement: {e}")
        return current_prompt  # Return the original prompt if there's an error

def process_message(message):
    """Process a message from the feedback_queue"""
    task_id = message.get('task_id')
    feedback_text = message.get('feedback_text')
    current_prompt = message.get('current_prompt')
    
    if not all([task_id, feedback_text, current_prompt]):
        print("Error: Invalid message format")
        return
    
    print(f"Processing feedback for task {task_id}")
    
    # Generate improved prompt
    new_prompt = generate_improved_prompt(current_prompt, feedback_text)
    
    # Update the task in the database
    db = next(get_db())
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            print(f"Error: Task {task_id} not found")
            return
        
        # Update the prompt
        task.current_prompt = new_prompt
        db.commit()
        
        print(f"Updated prompt for task {task_id}")
    finally:
        db.close()

def main():
    """Main function to consume messages from feedback_queue"""
    print("Feedback Processor service started")
    consume_queue("feedback_queue", process_message)

if __name__ == "__main__":
    main()
