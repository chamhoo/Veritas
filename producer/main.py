"""
Producer Service

Periodically checks database for active tasks and runs scrapers.
"""
import os
import sys
import time
import json
from datetime import datetime

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, init_db
from shared.models import Task, ProcessedItem
from shared.mq_utils import publish_message
from scrapers import RedditScraper, RssScraper


class Producer:
    def __init__(self):
        self.check_interval = int(os.getenv("PRODUCER_CHECK_INTERVAL", "300"))  # 5 minutes
        self.reddit_scraper = RedditScraper()
        self.rss_scraper = RssScraper()

    def get_scraper(self, source_type: str):
        """Get appropriate scraper based on source type."""
        if source_type == "reddit":
            return self.reddit_scraper
        elif source_type == "rss":
            return self.rss_scraper
        else:
            return None

    def process_task(self, task: Task):
        """
        Process a single task by running its scraper and publishing new items.
        """
        print(f"Processing task {task.id} (source: {task.source_type})")

        # Get scraper
        scraper = self.get_scraper(task.source_type)
        if not scraper:
            print(f"No scraper available for {task.source_type}")
            return

        # Parse source parameters
        try:
            params = json.loads(task.source_params)
        except json.JSONDecodeError:
            print(f"Invalid source_params for task {task.id}")
            return

        # Scrape content
        items = scraper.scrape(params)

        # Process each item
        new_items = 0
        with get_db() as db:
            for item in items:
                item_id = str(item.get("id", ""))
                if not item_id:
                    continue

                # Check if already processed
                existing = db.query(ProcessedItem).filter(
                    ProcessedItem.task_id == task.id,
                    ProcessedItem.item_id == item_id
                ).first()

                if existing:
                    # Already processed, skip
                    continue

                # Mark as processed
                processed = ProcessedItem(
                    task_id=task.id,
                    item_id=item_id,
                    processed_at=datetime.utcnow()
                )
                db.add(processed)
                db.flush()

                # Format content for filtering
                content = self.format_content(task.source_type, item)

                # Publish to raw content queue
                publish_message("raw_content_queue", {
                    "task_id": task.id,
                    "item": item,
                    "content": content
                })

                new_items += 1

        if new_items > 0:
            print(f"Published {new_items} new items for task {task.id}")

    def format_content(self, source_type: str, item: dict) -> str:
        """
        Format scraped item into readable content for LLM.
        """
        if source_type == "reddit":
            content = f"""Title: {item.get('title', '')}

Author: {item.get('author', 'Unknown')}
Score: {item.get('score', 0)}

Content:
{item.get('selftext', '')}

URL: {item.get('url', '')}
Permalink: {item.get('permalink', '')}
"""
        elif source_type == "rss":
            content = f"""Title: {item.get('title', '')}

Author: {item.get('author', 'Unknown')}
Published: {item.get('published', 'Unknown')}

Summary:
{item.get('summary', '')}

Link: {item.get('link', '')}
"""
        else:
            content = str(item)

        return content

    def run(self):
        """Main loop to check and process tasks."""
        print(f"Producer started. Checking tasks every {self.check_interval} seconds...")

        while True:
            try:
                with get_db() as db:
                    # Get all active tasks
                    tasks = db.query(Task).filter(Task.status == "active").all()

                    print(f"Found {len(tasks)} active tasks")

                    for task in tasks:
                        try:
                            self.process_task(task)
                        except Exception as e:
                            print(f"Error processing task {task.id}: {e}")

            except Exception as e:
                print(f"Error in main loop: {e}")

            time.sleep(self.check_interval)


def main():
    # Initialize database
    print("Initializing database...")
    init_db()

    # Start producer
    producer = Producer()
    producer.run()


if __name__ == "__main__":
    main()
