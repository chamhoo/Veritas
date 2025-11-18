import requests
import time

class RedditScraper:
    """Scraper for Reddit subreddits using the public JSON API."""

    def __init__(self):
        self.base_url = "https://www.reddit.com"
        self.headers = {
            'User-Agent': 'DynamicInfoPipeline/1.0 (Educational Project)'
        }
        self.last_request_time = 0
        self.min_request_interval = 2  # Respect Reddit's rate limits

    def _rate_limit(self):
        """Ensure we don't exceed Reddit's rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def scrape(self, subreddit, limit=25):
        """
        Scrape recent posts from a subreddit.

        Args:
            subreddit: Name of the subreddit (without /r/)
            limit: Number of posts to fetch (max 100)

        Returns:
            List of post dictionaries with id, title, content, url, author, created_utc
        """
        self._rate_limit()

        url = f"{self.base_url}/r/{subreddit}/new.json"
        params = {
            'limit': min(limit, 100),
            'raw_json': 1
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            posts = []

            for child in data.get('data', {}).get('children', []):
                post_data = child.get('data', {})

                # Build content from selftext or use title for link posts
                content = post_data.get('selftext', '')
                if not content:
                    content = post_data.get('title', '')

                post = {
                    'id': post_data.get('id', ''),
                    'title': post_data.get('title', ''),
                    'content': content,
                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                    'author': post_data.get('author', '[deleted]'),
                    'created_utc': post_data.get('created_utc', 0),
                    'score': post_data.get('score', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'subreddit': subreddit
                }

                posts.append(post)

            return posts

        except requests.exceptions.RequestException as e:
            print(f"Error scraping r/{subreddit}: {e}")
            return []
        except ValueError as e:
            print(f"Error parsing JSON from r/{subreddit}: {e}")
            return []
