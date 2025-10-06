import os
import time
import logging
import schedule
from typing import Dict, Any, List

from shared.database import Database
from shared.models import Task
from shared.mq_utils import RabbitMQClient
from producer.scrapers.reddit_scraper import RedditScraper
from producer.scrapers.rss_scraper import RssScraper

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

class Producer:
    """
    Service that periodically checks for active tasks and runs the appropriate scrapers.
    """
    def __init__(self):
        self.db = Database()
        self.mq_client = RabbitMQClient()
        self.scrapers = {
            'reddit': RedditScraper(),
            'rss': RssScraper()
        }
        self.raw_content_queue = "raw_content_queue"
        
        # Initialize database and message queue
        self.db.create_tables()
        self.mq_client.declare_queue(self.raw_content_queue)
        
        logger.info("Producer service initialized")
    
    def get_active_tasks(self) -> List[Task]:
        """Get all active tasks from the database."""
        with self.db.session_scope() as session:
            return Task.get_active_tasks(session)
    
    def process_task(self, task: Task) -> None:
        """Process a single task by running the appropriate scraper."""
        source_type = task.source_type
        source_target = task.source_target
        task_id = task.task_id
        
        if source_type not in self.scrapers:
            logger.error(f"Unknown source type: {source_type} for task {task_id}")
            return
        
        logger.info(f"Processing task {task_id}: {source_type} - {source_target}")
        
        # Get the appropriate scraper
        scraper = self.scrapers[source_type]
        
        # Get new content
        try:
            if source_type == 'reddit':
                new_items = scraper.get_new_posts(source_target, task_id)
            elif source_type == 'rss':
                new_items = scraper.get_new_entries(source_target, task_id)
            
            logger.info(f"Found {len(new_items)} new items for task {task_id}")
            
            # Publish each new item to the queue
            for item in new_items:
                self.publish_content(task_id, item)
                
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {str(e)}")
    
    def publish_content(self, task_id: int, content_data: Dict[str, Any]) -> None:
        """Publish new content to the raw_content_queue."""
        message = {
            "task_id": task_id,
            "data": content_data
        }
        
        self.mq_client.publish(self.raw_content_queue, message)
        logger.debug(f"Published content for task {task_id} to queue")
    
    def run_tasks(self) -> None:
        """Run all active tasks."""
        try:
            tasks = self.get_active_tasks()
            logger.info(f"Found {len(tasks)} active tasks")
            
            for task in tasks:
                self.process_task(task)
                
        except Exception as e:
            logger.error(f"Error in run_tasks: {str(e)}")
    
    def start(self) -> None:
        """Start the producer service."""
        # Schedule the task execution
        schedule.every(5).minutes.do(self.run_tasks)
        
        logger.info("Producer service started, running initial task scan...")
        # Initial run
        self.run_tasks()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    producer = Producer()
    producer.start()
