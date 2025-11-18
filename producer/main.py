import os
import sys
import time

# Add shared module to path
sys.path.insert(0, '/root/Veritas')

from dotenv import load_dotenv

from shared.database import get_session, init_db
from shared.models import Task, TaskStatus, SourceType, ProcessedItem
from shared.mq_utils import publish_message, RAW_CONTENT_QUEUE

sys.path.insert(0, '/root/Veritas/producer')
from scrapers import RedditScraper, RSSScraper

load_dotenv()

# Initialize scrapers
reddit_scraper = RedditScraper()
rss_scraper = RSSScraper()

def is_item_processed(session, task_id, item_id):
    """Check if an item has already been processed for a task."""
    exists = session.query(ProcessedItem).filter(
        ProcessedItem.task_id == task_id,
        ProcessedItem.item_id == item_id
    ).first()
    return exists is not None

def mark_item_processed(session, task_id, item_id):
    """Mark an item as processed for a task."""
    processed = ProcessedItem(
        task_id=task_id,
        item_id=item_id
    )
    session.add(processed)

def process_task(session, task):
    """Process a single task by scraping its source and publishing new content."""
    print(f"Processing task {task.id}: {task.source_type.value}:{task.source_identifier}")

    # Scrape based on source type
    if task.source_type == SourceType.REDDIT:
        items = reddit_scraper.scrape(task.source_identifier)
    elif task.source_type == SourceType.RSS:
        items = rss_scraper.scrape(task.source_identifier)
    else:
        print(f"Unknown source type: {task.source_type}")
        return

    new_items_count = 0

    for item in items:
        item_id = str(item.get('id', ''))

        # Skip if already processed
        if is_item_processed(session, task.id, item_id):
            continue

        # Prepare message for the queue
        message = {
            'task_id': task.id,
            'user_email': task.user_email,
            'item': item,
            'source_type': task.source_type.value,
            'source_identifier': task.source_identifier
        }

        # Publish to raw content queue
        try:
            publish_message(RAW_CONTENT_QUEUE, message)
            mark_item_processed(session, task.id, item_id)
            new_items_count += 1
        except Exception as e:
            print(f"Error publishing item {item_id}: {e}")
            continue

    if new_items_count > 0:
        session.commit()
        print(f"Published {new_items_count} new items for task {task.id}")
    else:
        print(f"No new items for task {task.id}")

def run_producer_cycle():
    """Run one cycle of the producer - check all active tasks."""
    session = get_session()

    try:
        # Get all active tasks
        tasks = session.query(Task).filter(
            Task.status == TaskStatus.ACTIVE
        ).all()

        print(f"Found {len(tasks)} active tasks")

        for task in tasks:
            try:
                process_task(session, task)
            except Exception as e:
                print(f"Error processing task {task.id}: {e}")
                session.rollback()
                continue

    except Exception as e:
        print(f"Error in producer cycle: {e}")
    finally:
        session.close()

def main():
    """Main function to run the producer service."""
    print("Starting Producer Service...")

    # Initialize database
    init_db()

    producer_interval = int(os.getenv('PRODUCER_INTERVAL', '300'))

    print(f"Producer interval: {producer_interval} seconds")

    while True:
        print("Running producer cycle...")
        run_producer_cycle()
        print(f"Sleeping for {producer_interval} seconds...")
        time.sleep(producer_interval)

if __name__ == '__main__':
    main()
