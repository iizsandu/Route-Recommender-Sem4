"""
NewsData.io Article Extractor
Fetches crime-related news articles from NewsData.io API
"""
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from article_text_extractor import ArticleTextExtractor
from newsdata_credit_manager import credit_manager
import os
from dotenv import load_dotenv

load_dotenv()


class NewsDataExtractor:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NewsData.io extractor
        
        Args:
            api_key: NewsData.io API key (or from .env)
        """
        self.api_key = api_key or os.getenv('NEWSDATA_API_KEY')
        if not self.api_key:
            raise ValueError("NewsData.io API key not found. Set NEWSDATA_API_KEY in .env")
        
        # Use /latest endpoint (works on free tier)
        self.base_url = "https://newsdata.io/api/1/latest"
        self.text_extractor = ArticleTextExtractor()
        
        # Crime-related keywords focused on Delhi
        self.keywords = [
            "Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft",
            "Delhi assault", "Delhi kidnapping", "Delhi rape", "Delhi burglary",
            "Delhi shooting", "Delhi stabbing", "Delhi gang", "Delhi fraud",
            "Delhi police arrest", "Delhi violence", "Delhi loot",
            "New Delhi crime", "NCR crime", "Noida crime", "Gurgaon crime",
        ]
    
    def fetch_articles(
        self,
        max_credits: int = 200,
        articles_per_credit: int = 10,
        delay_between_calls: float = 1.5
    ) -> List[Dict]:
        """
        Fetch articles from NewsData.io using latest endpoint
        
        Args:
            max_credits: Maximum API credits to use (default 200)
            articles_per_credit: Articles per API call (default 10)
            delay_between_calls: Delay between API calls in seconds
            
        Returns:
            List of article dictionaries
        """
        # Check credit status
        status = credit_manager.print_status()
        
        if not status['can_use']:
            print(f"❌ No credits available!")
            print(f"⏰ Credits will reset in {status['hours_until_reset']}h {status['minutes_until_reset']}m")
            return []
        
        # Adjust max_credits to available credits
        available_credits = status['credits_remaining']
        if max_credits > available_credits:
            print(f"⚠ Requested {max_credits} credits, but only {available_credits} available")
            print(f"⚠ Will use {available_credits} credits instead")
            max_credits = available_credits
        
        print(f"\n{'='*70}")
        print(f"NewsData.io Article Extraction")
        print(f"{'='*70}")
        print(f"Credits to use: {max_credits}/{available_credits} available")
        print(f"Articles per credit: {articles_per_credit}")
        print(f"Target articles: {max_credits * articles_per_credit}")
        print(f"Endpoint: /latest (free tier compatible)")
        print(f"Delay between calls: {delay_between_calls}s (avoid rate limit)")
        print(f"⏰ Credits reset in: {status['hours_until_reset']}h {status['minutes_until_reset']}m")
        print(f"{'='*70}\n")
        
        all_articles = []
        seen_urls = set()
        
        print(f"Keywords: {', '.join(self.keywords[:5])}...\n")
        
        credits_used = 0
        
        # Rotate through keywords to get diverse articles
        keyword_index = 0
        
        while credits_used < max_credits:
            # Use different keyword each iteration
            keyword = self.keywords[keyword_index % len(self.keywords)]
            keyword_index += 1
            
            print(f"[Credit {credits_used + 1}/{max_credits}] Fetching with keyword: '{keyword}'...")
            
            try:
                # Build API request
                params = {
                    'apikey': self.api_key,
                    'q': keyword,
                    'language': 'en',
                    'country': 'in',
                    'size': articles_per_credit
                }
                
                response = requests.get(self.base_url, params=params, timeout=30)
                
                # Check for errors
                if response.status_code == 403:
                    print(f"✗ API Error 403: Forbidden")
                    print(f"  Possible reasons:")
                    print(f"  1. Invalid API key")
                    print(f"  2. API key not activated")
                    print(f"  3. Free tier limit exceeded")
                    print(f"\n  Please check your API key at: https://newsdata.io/dashboard")
                    break
                
                if response.status_code == 429:
                    print("⚠ Rate limit hit, waiting 60 seconds...")
                    time.sleep(60)
                    continue
                
                if response.status_code != 200:
                    print(f"✗ API error: {response.status_code}")
                    print(f"  Response: {response.text[:200]}")
                    break
                
                data = response.json()
                
                if data.get('status') != 'success':
                    print(f"✗ API returned error: {data.get('message', 'Unknown error')}")
                    if 'results' in data:
                        print(f"  Details: {data.get('results', {})}")
                    break
                
                results = data.get('results', [])
                
                if not results:
                    print("  No articles found for this keyword")
                    # Still count as credit used
                    credits_used += 1
                    credit_manager.use_credits(1)
                    continue
                
                # Process articles
                new_articles = 0
                for article_data in results:
                    url = article_data.get('link')
                    
                    # Skip if duplicate
                    if not url or url in seen_urls:
                        continue
                    
                    seen_urls.add(url)
                    
                    # Create article object
                    article = {
                        'title': article_data.get('title', ''),
                        'url': url,
                        'source': f"NewsData.io - {article_data.get('source_id', 'Unknown')}",
                        'published_date': article_data.get('pubDate', ''),
                        'description': article_data.get('description', ''),
                        'extracted_at': datetime.now().isoformat(),
                        'full_text_extracted': False
                    }
                    
                    all_articles.append(article)
                    new_articles += 1
                
                print(f"  ✓ Fetched {new_articles} new articles (Total: {len(all_articles)})")
                
                credits_used += 1
                
                # Update credit manager
                credit_manager.use_credits(1)
                
                # Delay to avoid rate limiting
                if credits_used < max_credits:
                    time.sleep(delay_between_calls)
                
            except requests.exceptions.Timeout:
                print("✗ Request timeout, skipping...")
                continue
            except Exception as e:
                print(f"✗ Error: {e}")
                continue
        
        print(f"\n{'='*70}")
        print(f"NewsData.io Extraction Complete")
        print(f"{'='*70}")
        print(f"Credits used: {credits_used}")
        print(f"Unique articles fetched: {len(all_articles)}")
        
        # Show updated credit status
        final_status = credit_manager.get_status()
        print(f"Credits remaining: {final_status['credits_remaining']}/{final_status['max_credits']}")
        print(f"⏰ Reset in: {final_status['hours_until_reset']}h {final_status['minutes_until_reset']}m")
        print(f"{'='*70}\n")
        
        return all_articles
    


if __name__ == "__main__":
    # Test the extractor
    extractor = NewsDataExtractor()
    
    # Fetch 5 credits worth for testing
    articles = extractor.fetch_articles(max_credits=5)
    
    print(f"\nSample articles:")
    for i, article in enumerate(articles[:3], 1):
        print(f"\n{i}. {article['title']}")
        print(f"   URL: {article['url']}")
        print(f"   Source: {article['source']}")
        print(f"   Date: {article['published_date']}")
