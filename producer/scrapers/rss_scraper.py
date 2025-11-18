import feedparser
import hashlib
from datetime import datetime
import time

class RSSScraper:
    """Scraper for RSS/Atom feeds."""

    def __init__(self):
        self.timeout = 10

    def _generate_id(self, entry):
        """Generate a unique ID for an entry if none exists."""
        # Try to use existing ID
        if hasattr(entry, 'id') and entry.id:
            return entry.id

        # Generate from link
        if hasattr(entry, 'link') and entry.link:
            return hashlib.md5(entry.link.encode()).hexdigest()

        # Generate from title + published date
        content = f"{entry.get('title', '')}{entry.get('published', '')}"
        return hashlib.md5(content.encode()).hexdigest()

    def _parse_date(self, entry):
        """Extract and parse publication date from entry."""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

        for field in date_fields:
            if hasattr(entry, field) and getattr(entry, field):
                try:
                    return time.mktime(getattr(entry, field))
                except:
                    pass

        # Return current time as fallback
        return time.time()

    def _get_content(self, entry):
        """Extract content from entry."""
        # Try content field first
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].get('value', '')

        # Try summary
        if hasattr(entry, 'summary') and entry.summary:
            return entry.summary

        # Try description
        if hasattr(entry, 'description') and entry.description:
            return entry.description

        return ''

    def scrape(self, feed_url, limit=25):
        """
        Scrape recent entries from an RSS/Atom feed.

        Args:
            feed_url: URL of the RSS/Atom feed
            limit: Maximum number of entries to return

        Returns:
            List of entry dictionaries with id, title, content, url, author, created_utc
        """
        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                print(f"Error parsing feed {feed_url}: {feed.bozo_exception}")
                return []

            entries = []

            for entry in feed.entries[:limit]:
                item = {
                    'id': self._generate_id(entry),
                    'title': entry.get('title', 'No Title'),
                    'content': self._get_content(entry),
                    'url': entry.get('link', ''),
                    'author': entry.get('author', 'Unknown'),
                    'created_utc': self._parse_date(entry),
                    'feed_title': feed.feed.get('title', 'Unknown Feed'),
                    'feed_url': feed_url
                }

                entries.append(item)

            return entries

        except Exception as e:
            print(f"Error scraping feed {feed_url}: {e}")
            return []
