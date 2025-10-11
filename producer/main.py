import os
import time
import sys
import pickle
from sqlalchemy.orm import Session
sys.path.append('/app')

from shared.database import get_db, engine
from shared.models import Base, Task
from shared.mq_utils import publish_message
from scrapers.reddit_scraper import scrape_reddit
from scrapers.rss_scraper import scrape_rss

# Initialize database
Base.metadata.create_all(bind=engine)

# Configuration
CHECK_INTERVAL = int(os.getenv("PRODUCER_CHECK_INTERVAL", "300"))  # 5 minutes default
CACHE_FILE = "/app/producer/processed_items.pickle"

# In-memory cache of processed items
processed_items = {}

def load_processed_items():
    """Load previously processed items from disk"""
    global processed_items
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'rb') as f:
                processed_items = pickle.load(f)
            print(f"Loaded {sum(len(items) for items in processed_items.values())} processed items from cache")
    except Exception as e:
        print(f"Error loading processed items: {e}")
        processed_items = {}

def save_processed_items():
    """Save processed items to disk"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        
        # Save only the last 1000 items per task to prevent unlimited growth
        pruned_items = {}
        for task_id, items in processed_items.items():
            pruned_items[task_id] = list(items)[-1000:] if len(items) > 1000 else items
        
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(pruned_items, f)
    except Exception as e:
        print(f"Error saving processed items: {e}")

def is_processed(task_id, item_id):
    """Check if an item has already been processed for a task"""
    if task_id not in processed_items:
        processed_items[task_id] = set()
    return item_id in processed_items[task_id]

def mark_processed(task_id, item_id):
    """Mark an item as processed for a task"""
    if task_id not in processed_items:
        processed_items[task_id] = set()
    processed_items[task_id].add(item_id)

def scrape_and_publish(db: Session):
    """Scrape content for all active tasks and publish to queue"""
    tasks = db.query(Task).filter(Task.status == 'active').all()
    print(f"Found {len(tasks)} active tasks")
    
    for task in tasks:
        try:
            if task.source_type == 'reddit':
                items = scrape_reddit(task.source_target)
                source_type = 'reddit'
            elif task.source_type == 'rss':
                items = scrape_rss(task.source_target)
                source_type = 'rss'
            else:
                print(f"Unknown source type: {task.source_type}")
                continue
            
            print(f"Scraped {len(items)} items for task {task.task_id}")
            
            for item in items:
                # Generate a unique ID for this item
                item_id = f"{source_type}:{item['url']}"
                
                # Skip if already processed
                if is_processed(task.task_id, item_id):
                    continue
                
                # Publish to raw_content_queue
                publish_message("raw_content_queue", {
                    "task_id": task.task_id,
                    "data": item
                })
                
                # Mark as processed
                mark_processed(task.task_id, item_id)
                print(f"Published item {item_id} for task {task.task_id}")
        except Exception as e:
            print(f"Error scraping content for task {task.task_id}: {e}")
    
    # Save processed items periodically
    save_processed_items()

def main():
    """Main function to periodically check for new content"""
    print("Producer service started")
    
    # Load previously processed items
    load_processed_items()
    
    while True:
        try:
            db = next(get_db())
            try:
                scrape_and_publish(db)
            finally:
                db.close()
        except Exception as e:
            print(f"Error in main loop: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
