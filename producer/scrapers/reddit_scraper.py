"""
Reddit scraper using PRAW (Python Reddit API Wrapper).
"""
import os
import praw
from typing import List, Dict, Any


class RedditScraper:
    def __init__(self):
        """Initialize Reddit API client."""
        self.client_id = os.getenv("REDDIT_CLIENT_ID", "")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.user_agent = os.getenv("REDDIT_USER_AGENT", "DynamicPipeline/1.0")

        if not self.client_id or not self.client_secret:
            print("Warning: Reddit credentials not set. Reddit scraping will be limited.")
            self.reddit = None
        else:
            try:
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent
                )
                print("Reddit scraper initialized")
            except Exception as e:
                print(f"Failed to initialize Reddit client: {e}")
                self.reddit = None

    def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape Reddit posts from a subreddit.

        Args:
            params: Dictionary with 'subreddit' and optional 'limit'

        Returns:
            List of posts with id, title, selftext, url, author, created_utc
        """
        if not self.reddit:
            print("Reddit client not available")
            return []

        subreddit_name = params.get("subreddit", "all")
        limit = params.get("limit", 25)

        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []

            for submission in subreddit.new(limit=limit):
                posts.append({
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "url": submission.url,
                    "author": str(submission.author),
                    "created_utc": submission.created_utc,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "score": submission.score
                })

            print(f"Scraped {len(posts)} posts from r/{subreddit_name}")
            return posts

        except Exception as e:
            print(f"Error scraping Reddit: {e}")
            return []
