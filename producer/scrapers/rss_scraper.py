import feedparser
import logging
from typing import Dict, Any, List, Set
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class RssScraper:
    """
    Scraper for RSS feeds.
    """
    def __init__(self):
        self.processed_ids = {}  # task_id -> Set[entry_id]
    
    def get_new_entries(self, feed_url: str, task_id: int) -> List[Dict[str, Any]]:
        """
        Get new entries from an RSS feed.
        Returns a list of entry data dictionaries.
        """
        # Initialize processed IDs set for this task if it doesn't exist
        if task_id not in self.processed_ids:
            self.processed_ids[task_id] = set()
        
        # Fetch and parse the feed
        try:
            feed = feedparser.parse(feed_url)
            
            # Filter and process new entries
            new_entries = []
            for entry in feed.entries:
                # Generate a unique ID for the entry
                entry_id = self.generate_entry_id(entry)
                
                # Skip already processed entries
                if self.is_processed(task_id, entry_id):
                    continue
                
                # Mark as processed
                self.mark_processed(task_id, entry_id)
                
                # Clean and add to new entries
                new_entries.append(self.clean_content(entry))
                
            return new_entries
            
        except Exception as e:
            logger.error(f"Error fetching entries from {feed_url}: {str(e)}")
            return []
    
    def generate_entry_id(self, entry: Dict[str, Any]) -> str:
        """Generate a unique ID for an RSS entry."""
        # Use the entry's id if available
        if 'id' in entry:
            return entry.id
        
        # Otherwise, create a hash from the title and link
        content = f"{entry.get('title', '')}{entry.get('link', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_processed(self, task_id: int, entry_id: str) -> bool:
        """Check if an entry has already been processed for a task."""
        return entry_id in self.processed_ids.get(task_id, set())
    
    def mark_processed(self, task_id: int, entry_id: str) -> None:
        """Mark an entry as processed for a task."""
        if task_id not in self.processed_ids:
            self.processed_ids[task_id] = set()
        self.processed_ids[task_id].add(entry_id)
    
    def clean_content(self, raw_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and format the raw entry data."""
        return {
            "title": raw_entry.get("title", ""),
            "url": raw_entry.get("link", ""),
            "content": raw_entry.get("summary", ""),
            "author": raw_entry.get("author", ""),
            "published": raw_entry.get("published", ""),
            "source": raw_entry.get("source", {}).get("title", "RSS Feed")
        }
