import os
import logging
import asyncio
from typing import Dict, Any

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError

from shared.mq_utils import RabbitMQClient

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class Notifier:
    """
    Service that sends notifications to users via Telegram.
    """
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot = Bot(token=self.token)
        self.mq_client = RabbitMQClient()
        
        self.filtered_content_queue = "filtered_content_queue"
        
        # Initialize message queue
        self.mq_client.declare_queue(self.filtered_content_queue)
        
        logger.info("Notifier service initialized")
    
    def create_feedback_keyboard(self, task_id: int) -> InlineKeyboardMarkup:
        """Create feedback buttons for a notification."""
        keyboard = [
            [
                InlineKeyboardButton("👍 Relevant", callback_data=f"{task_id}:relevant"),
                InlineKeyboardButton("👎 Irrelevant", callback_data=f"{task_id}:irrelevant")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def send_notification(self, chat_id: int, message: str, task_id: int) -> None:
        """Send a notification to a user with feedback buttons."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=False,
                reply_markup=self.create_feedback_keyboard(task_id)
            )
            logger.info(f"Sent notification to chat {chat_id} for task {task_id}")
        except TelegramError as e:
            logger.error(f"Error sending notification to chat {chat_id}: {str(e)}")
    
    def process_message(self, message: Dict[str, Any]) -> None:
        """Process a message from the filtered_content_queue."""
        try:
            chat_id = message["telegram_chat_id"]
            formatted_message = message["formatted_message"]
            task_id = message["task_id"]
            
            logger.info(f"Sending notification to chat {chat_id} for task {task_id}")
            
            # Run the async sending function
            asyncio.run(self.send_notification(chat_id, formatted_message, task_id))
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def start(self) -> None:
        """Start consuming messages."""
        logger.info("Starting to consume messages from filtered_content_queue")
        self.mq_client.consume(self.filtered_content_queue, self.process_message)

if __name__ == "__main__":
    notifier = Notifier()
    notifier.start()
