import os
import logging
import requests
from typing import Dict, Any

from shared.database import Database
from shared.models import Task
from shared.mq_utils import RabbitMQClient

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class PromptImprover:
    """
    Class for improving prompts based on user feedback.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def improve_prompt(self, current_prompt: str, feedback: str) -> str:
        """
        Use the OpenRouter API to generate an improved prompt based on user feedback.
        Returns the new prompt.
        """
        # Format a meta-prompt
        meta_prompt = self.format_meta_prompt(current_prompt, feedback)
        
        # Create the messages for the API
        messages = [
            {"role": "system", "content": "You are an expert at writing filtering prompts for content. Your task is to improve the existing prompt based on user feedback."},
            {"role": "user", "content": meta_prompt}
        ]
        
        # Make the API request
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": "openai/gpt-3.5-turbo",
                    "messages": messages
                }
            )
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            improved_prompt = result["choices"][0]["message"]["content"].strip()
            
            return improved_prompt
            
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {str(e)}")
            return current_prompt  # Return the original prompt if there's an error
    
    def format_meta_prompt(self, current_prompt: str, feedback: str) -> str:
        """
        Format a meta-prompt for the OpenRouter API to improve the current prompt.
        """
        return f"""
        Here is the current prompt used to filter content:
        
        ```
        {current_prompt}
        ```
        
        The user provided this feedback on the results:
        
        ```
        {feedback}
        ```
        
        Based on this feedback, please generate an improved version of the prompt that will better match the user's expectations. 
        Return only the improved prompt text, without any additional explanations.
        """

class FeedbackProcessor:
    """
    Service that processes user feedback to improve prompts.
    """
    def __init__(self):
        self.db = Database()
        self.mq_client = RabbitMQClient()
        self.prompt_improver = PromptImprover()
        
        self.feedback_queue = "feedback_queue"
        
        # Initialize database and message queue
        self.db.create_tables()
        self.mq_client.declare_queue(self.feedback_queue)
        
        logger.info("Feedback Processor service initialized")
    
    def update_task_prompt(self, task_id: int, new_prompt: str) -> None:
        """Update a task's prompt in the database."""
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            if task:
                task.current_prompt = new_prompt
                logger.info(f"Updated prompt for task {task_id}")
            else:
                logger.error(f"No task found with ID {task_id}")
    
    def process_feedback(self, message: Dict[str, Any]) -> None:
        """Process a feedback message."""
        try:
            task_id = message["task_id"]
            feedback_text = message["feedback_text"]
            current_prompt = message["current_prompt"]
            
            logger.info(f"Processing feedback for task {task_id}")
            
            # Generate an improved prompt
            improved_prompt = self.prompt_improver.improve_prompt(current_prompt, feedback_text)
            
            # Update the task's prompt in the database
            self.update_task_prompt(task_id, improved_prompt)
            
            logger.info(f"Prompt updated for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}")
    
    def start(self) -> None:
        """Start consuming messages."""
        logger.info("Starting to consume messages from feedback_queue")
        self.mq_client.consume(self.feedback_queue, self.process_feedback)

if __name__ == "__main__":
    feedback_processor = FeedbackProcessor()
    feedback_processor.start()
