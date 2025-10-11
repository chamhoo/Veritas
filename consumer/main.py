import os
import json
import requests
from sqlalchemy.orm import Session
import sys
sys.path.append('/app')

from shared.database import get_db
from shared.models import Task
from shared.mq_utils import consume_queue, publish_message

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")

def call_llm(prompt, content):
    """Call the OpenRouter API to get a relevance decision"""
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set")
        return False, "API key not configured"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Prepare the message with the content to filter
    message_content = f"""
    I need to determine if the following content is relevant:
    
    TITLE: {content.get('title', 'No title')}
    URL: {content.get('url', 'No URL')}
    CONTENT: {content.get('content', 'No content')}
    
    Based on the user's filtering criteria:
    {prompt}
    """

    data = {
        "model": "openai/gpt-3.5-turbo",  # Use a default model, can be changed in .env
        "messages": [
            {"role": "system", "content": "You are a content relevance evaluator."},
            {"role": "user", "content": message_content}
        ]
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        assistant_response = result['choices'][0]['message']['content']
        
        # Check if the response contains YES (indicating relevance)
        is_relevant = 'YES' in assistant_response.upper()
        explanation = assistant_response
        
        return is_relevant, explanation
    except Exception as e:
        print(f"Error calling LLM API: {e}")
        return False, f"Error: {str(e)}"

def format_notification(task_id, content, explanation):
    """Format a notification email"""
    subject = f"New relevant content found: {content.get('title', 'No title')}"
    
    body = f"""
    We found content that matches your monitoring request (Task ID: {task_id}):
    
    Title: {content.get('title', 'No title')}
    URL: {content.get('url', 'No URL')}
    Author: {content.get('author', 'Unknown')}
    Date: {content.get('created', 'Unknown')}
    
    Content Preview:
    {content.get('content', 'No content')[:300]}...
    
    Why we thought this matched:
    {explanation}
    
    ---
    
    To provide feedback, simply reply to this email. Your feedback will help us improve the filtering.
    If this content wasn't relevant, let us know why.
    If you want more content like this, tell us what specific aspects you liked.
    
    Task ID: {task_id}
    """
    
    return subject, body

def process_message(message):
    """Process a message from the raw_content_queue"""
    task_id = message.get('task_id')
    content = message.get('data')
    
    if not task_id or not content:
        print("Error: Invalid message format")
        return
    
    print(f"Processing content for task {task_id}")
    
    # Get the task from the database
    db = next(get_db())
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            print(f"Error: Task {task_id} not found")
            return
        
        # Call the LLM to determine relevance
        is_relevant, explanation = call_llm(task.current_prompt, content)
        
        if is_relevant:
            print(f"Content is relevant for task {task_id}")
            
            # Format notification
            subject, body = format_notification(task_id, content, explanation)
            
            # Publish to filtered_content_queue
            publish_message("filtered_content_queue", {
                "user_email": task.user_email,
                "formatted_subject": subject,
                "formatted_body": body,
                "task_id_for_feedback": task_id
            })
        else:
            print(f"Content is not relevant for task {task_id}")
    finally:
        db.close()

def main():
    """Main function to consume messages from raw_content_queue"""
    print("Consumer service started")
    consume_queue("raw_content_queue", process_message)

if __name__ == "__main__":
    main()
