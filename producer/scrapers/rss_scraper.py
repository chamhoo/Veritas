"""
RSS feed scraper using feedparser.
"""
import feedparser
import hashlib
from typing import List, Dict, Any
from datetime import datetime


class RssScraper:
    def __init__(self):
        """Initialize RSS scraper."""
        print("RSS scraper initialized")

    def scrape(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape entries from an RSS feed.

        Args:
            params: Dictionary with 'url' key

        Returns:
            List of feed entries with id, title, summary, link, published
        """
        url = params.get("url", "")

        if not url:
            print("No RSS URL provided")
            return []

        try:
            feed = feedparser.parse(url)
            entries = []

            for entry in feed.entries:
                # Generate ID if not present
                entry_id = entry.get("id")
                if not entry_id:
                    # Use hash of link as ID
                    entry_id = hashlib.md5(entry.link.encode()).hexdigest()

                # Get published date
                published = entry.get("published", "")
                if not published and hasattr(entry, "published_parsed"):
                    published = datetime(*entry.published_parsed[:6]).isoformat()

                entries.append({
                    "id": entry_id,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", entry.get("description", "")),
                    "link": entry.get("link", ""),
                    "published": published,
                    "author": entry.get("author", "")
                })

            print(f"Scraped {len(entries)} entries from RSS feed")
            return entries

        except Exception as e:
            print(f"Error scraping RSS feed: {e}")
            return []
