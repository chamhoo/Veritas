import requests
import logging
from typing import Dict, Any, List, Set
import time

logger = logging.getLogger(__name__)

class RedditScraper:
    """
    Scraper for Reddit subreddits.
    """
    def __init__(self):
        self.user_agent = "Veritas/1.0"
        self.processed_ids = {}  # task_id -> Set[post_id]
        self.base_url = "https://www.reddit.com/r/{}/new.json"
    
    def get_new_posts(self, subreddit: str, task_id: int) -> List[Dict[str, Any]]:
        """
        Get new posts from a subreddit.
        Returns a list of post data dictionaries.
        """
        # Initialize processed IDs set for this task if it doesn't exist
        if task_id not in self.processed_ids:
            self.processed_ids[task_id] = set()
        
        # Construct the URL
        url = self.base_url.format(subreddit)
        
        # Make the request
        try:
            response = requests.get(
                url,
                headers={"User-Agent": self.user_agent},
                params={"limit": 25}
            )
            response.raise_for_status()
            
            data = response.json()
            posts = data["data"]["children"]
            
            # Filter and process new posts
            new_posts = []
            for post in posts:
                post_data = post["data"]
                post_id = post_data["id"]
                
                # Skip already processed posts
                if self.is_processed(task_id, post_id):
                    continue
                
                # Mark as processed
                self.mark_processed(task_id, post_id)
                
                # Clean and add to new posts
                new_posts.append(self.clean_content(post_data))
                
            return new_posts
            
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit}: {str(e)}")
            return []
    
    def is_processed(self, task_id: int, post_id: str) -> bool:
        """Check if a post has already been processed for a task."""
        return post_id in self.processed_ids.get(task_id, set())
    
    def mark_processed(self, task_id: int, post_id: str) -> None:
        """Mark a post as processed for a task."""
        if task_id not in self.processed_ids:
            self.processed_ids[task_id] = set()
        self.processed_ids[task_id].add(post_id)
    
    def clean_content(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and format the raw post data."""
        return {
            "title": raw_data.get("title", ""),
            "url": f"https://www.reddit.com{raw_data.get('permalink', '')}",
            "content": raw_data.get("selftext", ""),
            "author": raw_data.get("author", ""),
            "created_utc": raw_data.get("created_utc", 0),
            "subreddit": raw_data.get("subreddit", ""),
            "score": raw_data.get("score", 0),
        }
