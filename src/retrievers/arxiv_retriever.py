from typing import List, Dict
import aiohttp
import asyncio
import feedparser
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

async def RSS_searching(keywords: str, RSS_source_list=None) -> List[Dict]:
    """
    Input: a list of keywords.
    This code is used for searching the keywords into selected RSS source and returning back information as a list.
    Each information shoud be represented as an dict,
    {"title": the title of this RSS infomation, "source": like reddit or CNN..., "abstract": the abstarct of it, "links": the url}
    Ultimally, output a list of aboving dict
    """
    
    if RSS_source_list is None:
        RSS_source_list = ['arxiv']  # Default to Arxiv
    
    items_list = []
    
    for source in RSS_source_list:
        if source.lower() == 'arxiv':
            arxiv_results = await search_arxiv(keywords)
            items_list.extend(arxiv_results)
    
    return items_list

async def search_arxiv(keywords: str, max_results: int = 10, withindate=1) -> List[Dict]:
    """
    Search Arxiv using their API and return formatted results.
    Filters papers submitted within the last 'withindate' days.
    """
    try:
        # Arxiv API endpoint
        base_url = "http://export.arxiv.org/api/query"
        
        # Calculate the earliest allowed submission date
        earliest_date = datetime.now() - timedelta(days=withindate)
        earliest_date_str = earliest_date.strftime("%Y%m%d%H%M%S")[:-2]  # Format as YYYYMMDDHHMMSS
        current_date_str = datetime.now().strftime("%Y%m%d%H%M%S")[:-2]  # Current date in the same format
        # Construct the search query with date filter
        search_query = (
            f"search_query=all:{quote_plus(keywords)}+AND+submittedDate:[{earliest_date_str}+TO+{current_date_str}]"
            f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
        )

        full_url = f"http://export.arxiv.org/api/query?{search_query}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    print(f"Arxiv API error: {response.status}")
                    return []
                
                xml_content = await response.text()
                root = ET.fromstring(xml_content)
                
                # Define namespace
                namespace = {'atom': 'http://www.w3.org/2005/Atom'}
                
                items = []
                entries = root.findall('atom:entry', namespace)
                
                for entry in entries:
                    # Extract and clean data
                    title_elem = entry.find('atom:title', namespace)
                    title = title_elem.text.strip() if title_elem is not None else "No Title"
                    
                    summary_elem = entry.find('atom:summary', namespace)
                    abstract = summary_elem.text.strip() if summary_elem is not None else "No abstract available"
                    
                    link_elem = entry.find('atom:id', namespace)
                    link = link_elem.text.strip() if link_elem is not None else ""
                    
                    title = ' '.join(title.split())
                    abstract = ' '.join(abstract.split())
                    
                    if len(abstract) > 500:
                        abstract = abstract[:500] + "..."
                    
                    items.append({
                        "title": title,
                        "source": "Arxiv",
                        "abstract": abstract,
                        "links": link
                    })
                
                return items
                
    except Exception as e:
        print(f"Error searching Arxiv: {e}")
        return []

if __name__ == "__main__":
    async def test_rss_searching():
        """Test function for RSS_searching with Arxiv"""
        print("Testing RSS searcher with Arxiv...")
        
        # Test cases with different types of keywords
        test_cases = [
            "machine learning",
            "quantum computing",
            "neural networks deep learning",
            "computer vision",
            "natural language processing"
        ]
        
        for i, keywords in enumerate(test_cases, 1):
            print(f"\n--- Test Case {i}: '{keywords}' ---")
            try:
                results = await RSS_searching(keywords, ['arxiv'])
                
                if results:
                    print(f"Found {len(results)} results from Arxiv:")
                    for j, item in enumerate(results, 1):
                        print(f"\n{j}. Title: {item['title'][:100]}...")
                        print(f"   Source: {item['source']}")
                        print(f"   Abstract: {item['abstract'][:200]}...")
                        print(f"   Link: {item['links']}")
                else:
                    print("No results found.")
                    
            except Exception as e:
                print(f"Error during test: {e}")
            
            print("-" * 80)
        
        # Test with custom RSS source list
        print("\n--- Testing with custom RSS source list ---")
        try:
            results = await RSS_searching("artificial intelligence", ['arxiv'])
            print(f"Found {len(results)} results with custom source list")
        except Exception as e:
            print(f"Error with custom source list: {e}")
    
    # Run the test
    asyncio.run(test_rss_searching())