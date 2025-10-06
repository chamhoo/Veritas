import os
import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)

from shared.database import Database
from shared.models import Task
from shared.mq_utils import RabbitMQClient

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
AWAITING_SOURCE_TYPE = 0
AWAITING_SOURCE_TARGET = 1

class MasterBot:
    """
    Telegram bot that handles user commands and feedback.
    """
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.db = Database()
        self.mq_client = RabbitMQClient()
        self.feedback_queue = "feedback_queue"
        
        # Initialize database and message queue
        self.db.create_tables()
        self.mq_client.declare_queue(self.feedback_queue)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        await update.message.reply_text(
            "Welcome to Veritas! I can monitor information sources for you.\n\n"
            "Use /newtask to create a new monitoring task.\n"
            "Use /listtasks to see your current tasks.\n"
            "Use /pause <task_id> to pause a task.\n"
            "Use /resume <task_id> to resume a paused task.\n"
            "Use /delete <task_id> to delete a task."
        )
    
    async def new_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the conversation for creating a new task."""
        await update.message.reply_text(
            "Let's create a new monitoring task. First, what type of source do you want to monitor?\n\n"
            "Available sources: reddit, rss"
        )
        return AWAITING_SOURCE_TYPE
    
    async def process_source_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process the source type input and ask for source target."""
        source_type = update.message.text.lower()
        if source_type not in ["reddit", "rss"]:
            await update.message.reply_text(
                "Invalid source type. Please choose from: reddit, rss"
            )
            return AWAITING_SOURCE_TYPE
        
        context.user_data["source_type"] = source_type
        
        if source_type == "reddit":
            await update.message.reply_text(
                "Please enter the subreddit you want to monitor (e.g., 'python' for r/python):"
            )
        else:  # rss
            await update.message.reply_text(
                "Please enter the RSS feed URL you want to monitor:"
            )
        
        return AWAITING_SOURCE_TARGET
    
    async def process_source_target(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Process the source target and create the task."""
        source_target = update.message.text
        source_type = context.user_data["source_type"]
        
        # Generate an initial prompt for the task
        initial_prompt = self.generate_initial_prompt(
            source_type, source_target, f"Monitor {source_type} source {source_target}"
        )
        
        # Create a new task in the database
        with self.db.session_scope() as session:
            task = Task(
                user_id=update.effective_user.id,
                telegram_chat_id=update.effective_chat.id,
                source_type=source_type,
                source_target=source_target,
                current_prompt=initial_prompt,
                status="active"
            )
            session.add(task)
            session.flush()
            task_id = task.task_id
        
        await update.message.reply_text(
            f"Task #{task_id} created successfully!\n"
            f"I will monitor {source_type} source '{source_target}' for new content."
        )
        
        return ConversationHandler.END
    
    async def list_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List all tasks for the user."""
        user_id = update.effective_user.id
        
        with self.db.session_scope() as session:
            tasks = Task.get_user_tasks(session, user_id)
            
            if not tasks:
                await update.message.reply_text("You don't have any tasks.")
                return
            
            message = "Your tasks:\n\n"
            for task in tasks:
                status_emoji = "✅" if task.status == "active" else "⏸️"
                message += f"{status_emoji} Task #{task.task_id}: {task.source_type} - {task.source_target}\n"
            
            await update.message.reply_text(message)
    
    async def pause_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pause a specific task."""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Please provide a valid task ID: /pause <task_id>")
            return
        
        task_id = int(context.args[0])
        user_id = update.effective_user.id
        
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            
            if not task:
                await update.message.reply_text(f"Task #{task_id} not found.")
                return
                
            if task.user_id != user_id:
                await update.message.reply_text(f"You don't have permission to modify task #{task_id}.")
                return
                
            if task.status == "paused":
                await update.message.reply_text(f"Task #{task_id} is already paused.")
                return
                
            task.status = "paused"
            await update.message.reply_text(f"Task #{task_id} has been paused.")
    
    async def resume_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Resume a paused task."""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Please provide a valid task ID: /resume <task_id>")
            return
        
        task_id = int(context.args[0])
        user_id = update.effective_user.id
        
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            
            if not task:
                await update.message.reply_text(f"Task #{task_id} not found.")
                return
                
            if task.user_id != user_id:
                await update.message.reply_text(f"You don't have permission to modify task #{task_id}.")
                return
                
            if task.status == "active":
                await update.message.reply_text(f"Task #{task_id} is already active.")
                return
                
            task.status = "active"
            await update.message.reply_text(f"Task #{task_id} has been resumed.")
    
    async def delete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Delete a specific task."""
        if not context.args or not context.args[0].isdigit():
            await update.message.reply_text("Please provide a valid task ID: /delete <task_id>")
            return
        
        task_id = int(context.args[0])
        user_id = update.effective_user.id
        
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            
            if not task:
                await update.message.reply_text(f"Task #{task_id} not found.")
                return
                
            if task.user_id != user_id:
                await update.message.reply_text(f"You don't have permission to delete task #{task_id}.")
                return
                
            session.delete(task)
            await update.message.reply_text(f"Task #{task_id} has been deleted.")
    
    async def process_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Process feedback from notification buttons."""
        query = update.callback_query
        await query.answer()
        
        # Extract task_id and feedback_type from callback data
        # Format: "task_id:feedback_type" (e.g., "123:relevant")
        try:
            task_id, feedback_type = query.data.split(":")
            task_id = int(task_id)
        except (ValueError, IndexError):
            logger.error(f"Invalid callback data: {query.data}")
            return
        
        # Get the current prompt for the task
        with self.db.session_scope() as session:
            task = Task.get_by_id(session, task_id)
            if not task:
                await query.edit_message_text("Task not found.")
                return
            
            current_prompt = task.current_prompt
        
        # Send feedback to the feedback processor
        feedback_text = "This content is relevant and useful." if feedback_type == "relevant" else "This content is not relevant or useful."
        
        self.mq_client.publish(
            self.feedback_queue,
            {
                "task_id": task_id,
                "feedback_text": feedback_text,
                "current_prompt": current_prompt
            }
        )
        
        await query.edit_message_text(
            f"{query.message.text}\n\n✅ Feedback received: {feedback_type.capitalize()}"
        )
    
    def generate_initial_prompt(self, source_type: str, source_target: str, user_request: str) -> str:
        """Generate an initial LLM prompt based on the user's request."""
        return f"""
        You are evaluating content from {source_type} source '{source_target}'.
        Your task is to determine if the content is relevant to the user's request: "{user_request}".
        
        Respond with 'YES' if the content is relevant, or 'NO' if it is not relevant.
        Include a brief explanation of your decision.
        """
    
    def run(self):
        """Start the bot."""
        application = Application.builder().token(self.token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start))
        
        # New task conversation handler
        new_task_conv = ConversationHandler(
            entry_points=[CommandHandler("newtask", self.new_task)],
            states={
                AWAITING_SOURCE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_source_type)],
                AWAITING_SOURCE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_source_target)]
            },
            fallbacks=[CommandHandler("start", self.start)]
        )
        application.add_handler(new_task_conv)
        
        # Other command handlers
        application.add_handler(CommandHandler("listtasks", self.list_tasks))
        application.add_handler(CommandHandler("pause", self.pause_task))
        application.add_handler(CommandHandler("resume", self.resume_task))
        application.add_handler(CommandHandler("delete", self.delete_task))
        
        # Callback query handler for buttons
        application.add_handler(CallbackQueryHandler(self.process_feedback))
        
        # Start the bot
        logger.info("Master Bot started")
        application.run_polling()


if __name__ == "__main__":
    bot = MasterBot()
    bot.run()
