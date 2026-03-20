"""
Google News Article Extractor using GoogleNews Library
Fetches actual article URLs (not RSS redirects) and extracts full text
Auto-saves progress to prevent data loss on rate limits
Uses centralized ArticleTextExtractor for all text extraction
"""
from GoogleNews import GoogleNews
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import random
from typing import List, Dict
import json
import os
from article_text_extractor import get_extractor

class GoogleNewsExtractor:
    def __init__(self, auto_save_file: str = "google_news_progress.json"):
        self.rate_limit_hits = 0
        self.MAX_RATE_LIMITS = 10
        self.auto_save_file = auto_save_file
        self.all_articles = []
        self.seen_urls = set()
        # Use centralized extractor
        self.text_extractor = get_extractor()
        
    def save_progress(self):
        """Save current progress to file"""
        try:
            data = {
                'articles': self.all_articles,
                'seen_urls': list(self.seen_urls),
                'total_articles': len(self.all_articles),
                'saved_at': datetime.now().isoformat()
            }
            with open(self.auto_save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            print(f"\n💾 Progress saved: {len(self.all_articles)} articles")
        except Exception as e:
            print(f"\n⚠️  Failed to save progress: {e}")
    
    def load_progress(self) -> bool:
        """Load previous progress if exists"""
        if os.path.exists(self.auto_save_file):
            try:
                with open(self.auto_save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.all_articles = data.get('articles', [])
                self.seen_urls = set(data.get('seen_urls', []))
                print(f"\n📂 Loaded previous progress: {len(self.all_articles)} articles")
                return True
            except Exception as e:
                print(f"\n⚠️  Failed to load progress: {e}")
        return False
        
    
    def fetch_articles(self, 
                      keywords: List[str] = None,
                      start_date: datetime = None,
                      end_date: datetime = None,
                      pages_per_keyword: int = 20,
                      target_articles: int = 5000) -> List[Dict]:
        """
        Fetch articles from Google News using GoogleNews library
        Auto-saves progress every 50 articles and on rate limits
        
        Args:
            keywords: List of search keywords
            start_date: Start date for article search
            end_date: End date for article search
            pages_per_keyword: Number of pages to fetch per keyword
            target_articles: Target number of articles to extract
            
        Returns:
            List of articles with full text extracted
        """
        if not keywords:
            keywords = [
                # Delhi crimes
                "Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft", 
                "Delhi assault", "Delhi rape", "Delhi kidnapping"
                # # Mumbai crimes
                # "Mumbai crime", "Mumbai murder", "Mumbai robbery", "Mumbai theft",
                # # Bangalore crimes
                # "Bangalore crime", "Bangalore murder", "Bangalore robbery",
                # # Chennai crimes
                # "Chennai crime", "Chennai murder", "Chennai robbery",
                # # Kolkata crimes
                # "Kolkata crime", "Kolkata murder", "Kolkata robbery",
                # # Hyderabad crimes
                # "Hyderabad crime", "Hyderabad murder", "Hyderabad robbery",
                # # General India
                # "India crime news", "India murder", "India robbery",
                # "India violent crime", "India theft"
            ]
        
        if not start_date:
            start_date = datetime(2025, 6, 1)  # Extended date range
        
        if not end_date:
            end_date = datetime(2026, 3, 1)
        
        # Load previous progress if exists
        self.load_progress()
        
        print(f"\n{'='*70}")
        print(f"Google News Article Extraction - Target: {target_articles} articles")
        print(f"{'='*70}")
        print(f"Keywords: {len(keywords)}")
        print(f"Date Range: {start_date.strftime('%m/%d/%Y')} to {end_date.strftime('%m/%d/%Y')}")
        print(f"Pages per keyword: {pages_per_keyword}")
        print(f"Starting with: {len(self.all_articles)} existing articles")
        print(f"{'='*70}\n")
        
        current_date = start_date
        save_counter = 0
        
        try:
            while current_date < end_date and len(self.all_articles) < target_articles:
                next_month = current_date + relativedelta(months=1)
                period_start = current_date.strftime('%m/%d/%Y')
                period_end = next_month.strftime('%m/%d/%Y')
                
                print(f"\n📅 Period: {period_start} to {period_end}")
                print(f"Progress: {len(self.all_articles)}/{target_articles} articles")
                print(f"{'='*70}\n")
                
                for keyword in keywords:
                    if self.rate_limit_hits >= self.MAX_RATE_LIMITS:
                        print("\n⚠️  Rate limit threshold reached. Saving and stopping...")
                        self.save_progress()
                        return self.all_articles
                    
                    if len(self.all_articles) >= target_articles:
                        print(f"\n✓ Target reached: {len(self.all_articles)} articles")
                        self.save_progress()
                        return self.all_articles
                    
                    print(f"🔍 Searching: '{keyword}'")
                    
                    try:
                        googlenews = GoogleNews(lang='en')
                        googlenews.set_time_range(period_start, period_end)
                        googlenews.search(keyword)
                        
                        for page in range(1, pages_per_keyword + 1):
                            if len(self.all_articles) >= target_articles:
                                break
                            
                            print(f"  📄 Page {page}/{pages_per_keyword}...", end=" ")
                            
                            try:
                                googlenews.get_page(page)
                                results = googlenews.results()
                                
                                if not results:
                                    print("No results")
                                    time.sleep(10)
                                    continue
                                
                                new_articles = 0
                                for news in results:
                                    url = news.get('link', '')
                                    
                                    if url and url not in self.seen_urls:
                                        self.seen_urls.add(url)
                                        
                                        # Extract full text using centralized extractor
                                        full_content = self.text_extractor.extract(url, source='Google News', keyword=keyword)
                                        
                                        article = {
                                            'url': full_content['url'],
                                            'title': full_content['title'] or news.get('title', ''),
                                            'date': full_content['publish_date'],
                                            'text': full_content['text'],
                                            'summary': full_content['summary'],
                                            'source': 'Google News',
                                            'keyword': keyword,
                                            'extracted_at': full_content['extracted_at'],
                                            'full_text_extracted': full_content['full_text_extracted']
                                        }
                                        
                                        self.all_articles.append(article)
                                        new_articles += 1
                                        save_counter += 1
                                        
                                        # Auto-save every 50 articles
                                        if save_counter >= 50:
                                            self.save_progress()
                                            save_counter = 0
                                
                                print(f"✓ {len(results)} results, {new_articles} new (Total: {len(self.all_articles)})")
                                
                                # Rate limiting
                                sleep_time = random.uniform(3, 7)
                                time.sleep(sleep_time)
                                
                            except Exception as e:
                                print(f"✗ Error: {str(e)[:40]}")
                                self.rate_limit_hits += 1
                                wait = random.uniform(30, 60)
                                print(f"  ⏳ Sleeping {wait:.1f}s... (Rate limit hits: {self.rate_limit_hits})")
                                
                                # Save before long wait
                                self.save_progress()
                                time.sleep(wait)
                                
                                if self.rate_limit_hits >= self.MAX_RATE_LIMITS:
                                    break
                        
                        print(f"  ✓ Completed '{keyword}': {len(self.all_articles)} total articles\n")
                        
                    except Exception as e:
                        print(f"  ✗ Error with keyword '{keyword}': {e}\n")
                        self.save_progress()
                        continue
                
                if self.rate_limit_hits >= self.MAX_RATE_LIMITS:
                    break
                
                current_date = next_month
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user. Saving progress...")
            self.save_progress()
            return self.all_articles
        
        except Exception as e:
            print(f"\n\n⚠️  Unexpected error: {e}. Saving progress...")
            self.save_progress()
            return self.all_articles
        
        # Final save
        self.save_progress()
        
        print(f"\n{'='*70}")
        print(f"Extraction Complete!")
        print(f"{'='*70}")
        print(f"Total unique articles fetched: {len(self.all_articles)}")
        print(f"Articles with full text: {sum(1 for a in self.all_articles if a['full_text_extracted'])}")
        print(f"{'='*70}\n")
        
        return self.all_articles
