import os
import requests
import time
from datetime import datetime, timedelta

# Configuration
USER_AGENT = "Veritas/1.0 (by /u/VeritasBot)"
REDDIT_LIMIT = int(os.getenv("REDDIT_LIMIT", "25"))  # Number of posts to fetch

def scrape_reddit(subreddit):
    """
    Scrape posts from a subreddit
    
    Args:
        subreddit: Subreddit name (e.g., "r/python" or just "python")
    
    Returns:
        List of dictionaries containing post data
    """
    # Normalize subreddit name
    if subreddit.startswith('r/'):
        subreddit = subreddit[2:]
    
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={REDDIT_LIMIT}"
    
    headers = {
        "User-Agent": USER_AGENT
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        posts = data['data']['children']
        
        # Process posts into standard format
        results = []
        for post in posts:
            post_data = post['data']
            
            # Get post creation time
            created_utc = post_data.get('created_utc', 0)
            post_time = datetime.fromtimestamp(created_utc)
            
            # Only include posts from the last 24 hours
            if datetime.now() - post_time > timedelta(hours=24):
                continue
            
            content = post_data.get('selftext', '')
            if not content and 'url' in post_data:
                content = f"Link post: {post_data['url']}"
            
            results.append({
                'title': post_data.get('title', ''),
                'url': f"https://www.reddit.com{post_data.get('permalink', '')}",
                'content': content,
                'author': post_data.get('author', 'unknown'),
                'created': post_time.isoformat(),
                'score': post_data.get('score', 0)
            })
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"Error scraping Reddit: {e}")
        return []
