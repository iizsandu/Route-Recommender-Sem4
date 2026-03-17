"""
Article Extractor
Extracts crime news articles from multiple sources
Uses centralized ArticleTextExtractor for all text extraction
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import time
from article_text_extractor import get_extractor

class ArticleExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.crime_keywords = [
            'crime', 'murder', 'robbery', 'theft', 'assault', 'rape', 'kidnapping',
            'arrested', 'held', 'killed', 'dead', 'body', 'attack', 'shot', 'stabbed',
            'police', 'accused', 'victim', 'gang', 'fraud', 'scam', 'burglary', 'loot'
        ]
        # Delhi-specific pages to scrape
        self.toi_delhi_urls = [
            "https://timesofindia.indiatimes.com/city/delhi",
            "https://timesofindia.indiatimes.com/topic/delhi-crime",
            "https://timesofindia.indiatimes.com/topic/delhi-police",
            "https://timesofindia.indiatimes.com/topic/delhi-murder",
        ]
        # Use centralized extractor
        self.text_extractor = get_extractor()
    
    def extract_from_times_of_india(self, max_articles: int = 50) -> List[Dict]:
        """Extract crime articles from Times of India - Delhi focused"""
        articles = []
        seen_urls = set()

        for page_url in self.toi_delhi_urls:
            if len(articles) >= max_articles:
                break
            try:
                response = requests.get(page_url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    print(f"  ✗ Failed to fetch {page_url} (status {response.status_code})")
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')
                article_links = soup.find_all('a', href=True)

                for link in article_links:
                    if len(articles) >= max_articles:
                        break

                    href = link.get('href', '')
                    title = link.get_text(strip=True)

                    if not href or not title:
                        continue

                    # Must contain a crime keyword
                    if not any(kw in title.lower() for kw in self.crime_keywords):
                        continue

                    full_url = href if href.startswith('http') else f"https://timesofindia.indiatimes.com{href}"

                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    print(f"  Extracting: {full_url[:80]}...")
                    result = self.text_extractor.extract(full_url, source='Times of India')

                    article = {
                        'url': result['url'],
                        'title': result['title'] or title,
                        'date': result['publish_date'],
                        'text': result['text'],
                        'summary': result['summary'],
                        'source': 'Times of India',
                        'extracted_at': result['extracted_at'],
                        'description': '',
                        'full_text_extracted': result['full_text_extracted']
                    }

                    articles.append(article)
                    time.sleep(0.5)

            except Exception as e:
                print(f"  Error fetching {page_url}: {e}")

        return articles
    
    def extract_articles(self, sources: List[str] = None) -> List[Dict]:
        """Extract articles from multiple sources"""
        all_articles = []
        
        if not sources:
            sources = ['times_of_india']
        
        if 'times_of_india' in sources:
            print("Extracting from Times of India...")
            all_articles.extend(self.extract_from_times_of_india(max_articles=100))
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        return unique_articles
