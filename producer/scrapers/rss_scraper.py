import feedparser
from datetime import datetime, timedelta
import time
import requests
from urllib.parse import urlparse

def is_valid_url(url):
    """Check if a URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def scrape_rss(feed_url):
    """
    Scrape posts from an RSS feed
    
    Args:
        feed_url: URL of the RSS feed
    
    Returns:
        List of dictionaries containing post data
    """
    if not is_valid_url(feed_url):
        print(f"Invalid feed URL: {feed_url}")
        return []
    
    try:
        # Set a timeout to avoid hanging on slow feeds
        feed = feedparser.parse(feed_url)
        
        if feed.get('bozo_exception'):
            print(f"Warning: Feed may be malformed: {feed.bozo_exception}")
        
        entries = feed.get('entries', [])
        
        # Process entries into standard format
        results = []
        for entry in entries:
            # Try to parse publication date
            published = entry.get('published', entry.get('updated', None))
            if published:
                try:
                    dt = datetime(*published[:6])
                except:
                    # Try parsing as string
                    try:
                        dt = datetime.strptime(published, '%a, %d %b %Y %H:%M:%S %z')
                    except:
                        dt = None
            else:
                dt = None
            
            # Skip entries older than 24 hours if we can determine the date
            if dt and datetime.now() - dt > timedelta(hours=24):
                continue
            
            # Get content
            content = entry.get('description', entry.get('summary', ''))
            if not content and 'content' in entry and len(entry.content) > 0:
                content = entry.content[0].value
            
            results.append({
                'title': entry.get('title', 'No title'),
                'url': entry.get('link', ''),
                'content': content,
                'author': entry.get('author', 'unknown'),
                'created': dt.isoformat() if dt else datetime.now().isoformat(),
            })
        
        return results
        
    except Exception as e:
        print(f"Error scraping RSS feed {feed_url}: {e}")
        return []
