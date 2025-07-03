import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from urllib.parse import urlparse, parse_qs, unquote
from typing import List, Dict
import re

async def scrape_website_searching(keywords: str, n_results=5) -> List[Dict]:
    """
    Input: a list of keywords.
    This code is used for searching the keywords into internet(using google or duckduckgo or other headless searching tools) and returning back top N websits as a list.
    Each website shoud be represented as an dict,
    {"title": the title of this website, "source": like reddit or CNN..., "abstract": the abstarct of this website}
    Ultimally, output a list of aboving dict
    """
    
    async def search_duckduckgo(query: str, max_results: int = 10) -> List[str]:
        """Search DuckDuckGo and return URLs"""
        encoded_query = quote_plus(query)
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(search_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }) as response:
                    html = await response.text()
                    
                soup = BeautifulSoup(html, 'html.parser')
                urls = []
                
                for result in soup.find_all('a', class_='result__url')[:max_results]:
                    href = result.get('href')
                    if href:
                        # extract herf
                        full_url = "https:" + href
                        parsed_url = urlparse(full_url)
                        query_params = parse_qs(parsed_url.query)
                        encoded_url = query_params['uddg'][0]
                        clean_url = unquote(encoded_url)
                        urls.append(clean_url)
                
                return urls
            except Exception as e:
                print(f"Search error: {e}")
                return []
    
    async def extract_website_info(url: str, session: aiohttp.ClientSession) -> Dict:
        """Extract title, source, and abstract from a website"""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }) as response:
                if response.status != 200:
                    return None
                    
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract title
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else "No Title"
                
                # Extract source from domain
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                source = parsed_url.netloc.replace('www.', '').split('.')[0].title()
                
                # Extract abstract (try multiple methods)
                abstract = ""
                
                # Try meta description first
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    abstract = meta_desc.get('content', '').strip()
                
                # If no meta description, try to get first paragraph
                if not abstract:
                    paragraphs = soup.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if len(text) > 100:  # Skip very short paragraphs
                            abstract = text[:300] + "..." if len(text) > 300 else text
                            break
                
                # Clean up abstract
                abstract = re.sub(r'\s+', ' ', abstract).strip()
                if not abstract:
                    abstract = "No description available"
                
                return {
                    "title": title,
                    "url": url,
                    "source": source,
                    "abstract": abstract
                }
                
        except Exception as e:
            print(f"Error extracting from {url}: {e}")
            return None
    
    # Main execution
    try:
        # Search for URLs
        urls = await search_duckduckgo(keywords, max_results=n_results)
        
        if not urls:
            return []
        
        # Extract information from each URL
        items_list = []
        async with aiohttp.ClientSession() as session:
            tasks = [extract_website_info(url, session) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result:
                    items_list.append(result)
        
        return items_list # Return top 5 results
        
    except Exception as e:
        print(f"Error in scrape_website: {e}")
        return []

if __name__ == "__main__":
    async def test_scrape_website():
        """Test function for scrape_website"""
        print("Testing web scraper...")
        
        # Test cases with different types of keywords
        test_cases = [
            "Python programming tutorials",
            "artificial intelligence news",
            "climate change research 2024"
        ]
        
        for i, keywords in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i}: '{keywords}' ---")
            try:
                results = await scrape_website_searching(keywords)
                
                if results:
                    print(f"Found {len(results)} results:")
                    for j, item in enumerate(results, 1):
                        print(f"\n{j}. Title: {item['title'][:80]}...")
                        print(f"   Source: {item['source']}")
                        print(f"   Abstract: {item['abstract'][:150]}...")
                else:
                    print("No results found.")
                    
            except Exception as e:
                print(f"Error during test: {e}")
            
            print("-" * 50)
    
    # Run the test
    asyncio.run(test_scrape_website())