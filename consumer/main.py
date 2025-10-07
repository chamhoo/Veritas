import os
import logging
import json
import time
import requests
from typing import Dict, Any, Optional

from shared.database import Database
from shared.models import Task
from shared.mq_utils import RabbitMQClient

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class OpenRouterClient:
    """
    Client for interacting with the OpenRouter LLM API.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def is_content_relevant(self, prompt: str, content: Dict[str, Any]) -> bool:
        """
        Determine if the content is relevant based on the prompt.
        Returns True if the content is relevant, False otherwise.
        """
        # Format content for the LLM
        content_text = f"Title: {content.get('title', '')}\nURL: {content.get('url', '')}\nContent: {content.get('content', '')}"
        
        # Create the messages for the API
        messages = [
            {"role": "system", "content": "You are a content filter. Respond with ONLY 'YES' or 'NO' - nothing else."},
            {"role": "user", "content": f"{prompt}\n\nContent to evaluate:\n{content_text}"}
        ]
        
        # Make the API request with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "model": "openai/gpt-3.5-turbo",
                        "messages": messages,
                        "temperature": 0.3,
                        "max_tokens": 10
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                answer_text = result["choices"][0]["message"]["content"].strip().upper()
                
                # Check if the answer starts with YES
                is_relevant = answer_text.startswith("YES")
                logger.debug(f"LLM response: {answer_text}, relevant: {is_relevant}")
                return is_relevant
                
            except requests.exceptions.Timeout:
                logger.warning(f"API request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except requests.exceptions.RequestException as e:
                logger.error(f"API request error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            except (KeyError, IndexError, ValueError) as e:
                logger.error(f"Error parsing API response: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error calling OpenRouter API: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
        
        logger.error("Failed to get API response after all retries")
        return False

class Consumer:
    """
    Service that filters content using LLM to determine relevance.
    """
    def __init__(self):
        self.db = Database()
        self.mq_client = RabbitMQClient()
        self.llm_client = OpenRouterClient()
        
        self.raw_content_queue = "raw_content_queue"
        self.filtered_content_queue = "filtered_content_queue"
        
        # Initialize database and message queues
        self.db.create_tables()
        self.mq_client.declare_queue(self.raw_content_queue)
        self.mq_client.declare_queue(self.filtered_content_queue)
        
        logger.info("Consumer service initialized")
    
    def get_task_prompt(self, task_id: int) -> Optional[str]:
        """Get the current prompt for a task."""
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            if task:
                return task.current_prompt
            return None
    
    def get_chat_id(self, task_id: int) -> Optional[int]:
        """Get the telegram_chat_id for a task."""
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            if task:
                return task.telegram_chat_id
            return None
    
    def format_message(self, content: Dict[str, Any], task_id: int) -> str:
        """Format a notification message with the content."""
        title = content.get('title', 'No title')
        url = content.get('url', '#')
        summary = content.get('content', '')[:150] + '...' if len(content.get('content', '')) > 150 else content.get('content', '')
        source = content.get('source', content.get('subreddit', 'Unknown source'))
        
        return (
            f"🔔 *New relevant content for Task #{task_id}*\n\n"
            f"*{title}*\n\n"
            f"{summary}\n\n"
            f"Source: {source}\n"
            f"[Read more]({url})"
        )
    
    def process_message(self, message: Dict[str, Any]) -> None:
        """Process a message from the raw_content_queue."""
        try:
            task_id = message["task_id"]
            content = message["data"]
            
            logger.info(f"Processing content for task {task_id}")
            
            # Get the prompt for this task
            prompt = self.get_task_prompt(task_id)
            if not prompt:
                logger.error(f"No prompt found for task {task_id}")
                return
            
            # Check if the content is relevant
            if self.llm_client.is_content_relevant(prompt, content):
                logger.info(f"Content is relevant for task {task_id}")
                
                # Get the chat ID for this task
                chat_id = self.get_chat_id(task_id)
                if not chat_id:
                    logger.error(f"No chat ID found for task {task_id}")
                    return
                
                # Format the message
                formatted_message = self.format_message(content, task_id)
                
                # Publish to the filtered_content_queue
                self.mq_client.publish(
                    self.filtered_content_queue,
                    {
                        "telegram_chat_id": chat_id,
                        "formatted_message": formatted_message,
                        "task_id": task_id
                    }
                )
                
                logger.info(f"Published notification for task {task_id}")
            else:
                logger.info(f"Content is not relevant for task {task_id}")
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def start(self) -> None:
        """Start consuming messages."""
        logger.info("Starting to consume messages from raw_content_queue")
        self.mq_client.consume(self.raw_content_queue, self.process_message)

if __name__ == "__main__":
    consumer = Consumer()
    consumer.start()
