"""
Unified Article Extractor
Combines all extraction methods and runs indefinitely until timeout/error
Uses centralized ArticleTextExtractor for all text extraction
"""
from google_news_extractor import GoogleNewsExtractor
from toi_extractor import ArticleExtractor
from newsdata_extractor import NewsDataExtractor
from hindu_extractor import HinduExtractor
from ndtv_extractor import NDTVExtractor
from indian_express_extractor import IndianExpressExtractor
from db_handler import DBHandler
from datetime import datetime
import time
import json
import os
from typing import List, Dict
from article_text_extractor import get_extractor

class UnifiedExtractor:
    def __init__(self, auto_save_interval: int = 50, cancel_event=None):
        self.google_news_extractor = GoogleNewsExtractor()
        self.times_of_india_extractor = ArticleExtractor()
        self.newsdata_extractor = NewsDataExtractor()
        self.hindu_extractor = HinduExtractor()
        self.ndtv_extractor = NDTVExtractor()
        self.indian_express_extractor = IndianExpressExtractor()
        self.text_extractor = get_extractor()
        self.auto_save_interval = auto_save_interval
        self.cancel_event = cancel_event
        self.all_articles = []
        self.seen_urls = set()
        self.save_counter = 0
        self.progress_file = "extraction_progress.json"
        self.error_count = 0
        self.max_errors = 10
        
    def save_progress(self):
        """Save current progress to file and database"""
        try:
            # Save to JSON file
            data = {
                'articles': self.all_articles,
                'seen_urls': list(self.seen_urls),
                'total_articles': len(self.all_articles),
                'saved_at': datetime.now().isoformat(),
                'error_count': self.error_count
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Save to database
            if self.all_articles:
                db = DBHandler(collection_name="articles2")
                if db.connected:
                    result = db.save_articles(self.all_articles)
                    print(f"\n💾 Saved to DB: {result['inserted']} new, {result['duplicates']} duplicates")
                    # Clear saved articles to avoid re-saving
                    self.all_articles = []
                    self.save_counter = 0
            
            print(f"💾 Progress saved: {len(self.seen_urls)} total URLs processed")
            
        except Exception as e:
            print(f"\n⚠️  Failed to save progress: {e}")
    
    def load_progress(self) -> bool:
        """Load previous progress if exists"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.all_articles = data.get('articles', [])
                self.seen_urls = set(data.get('seen_urls', []))
                self.error_count = data.get('error_count', 0)
                print(f"\n📂 Loaded previous progress: {len(self.seen_urls)} URLs processed")
                return True
            except Exception as e:
                print(f"\n⚠️  Failed to load progress: {e}")
        return False
    
    def extract_from_google_news(self, keywords: List[str], max_articles: int = 200) -> int:
        """Extract from Google News (RSS + decoder + gnews) - returns count of new articles"""
        if self.cancel_event and self.cancel_event.is_set():
            return 0
        try:
            articles = self.google_news_extractor.extract(
                keywords=keywords,
                max_articles=max_articles,
                seen_urls=set(self.seen_urls)
            )
            count = self._ingest_articles(articles)
            print(f"✓ Google News: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"✗ Google News error: {str(e)[:80]}")
            self.error_count += 1
            return 0
    
    def extract_from_times_of_india(self, max_articles: int = 100) -> int:
        """Extract from Times of India - returns count of new articles"""
        print(f"\n{'='*70}")
        print(f"📰 Times of India Extraction")
        print(f"{'='*70}")
        
        new_count = 0
        
        try:
            articles = self.times_of_india_extractor.extract_from_times_of_india(max_articles=max_articles)
            
            for article in articles:
                # Check cancellation
                if self.cancel_event and self.cancel_event.is_set():
                    print(f"\n🛑 Cancellation requested. Saving progress...")
                    self.save_progress()
                    return new_count

                url = article.get('url', '')
                
                # Clean URL using centralized extractor
                clean_url = self.text_extractor.clean_url(url)
                
                if clean_url and clean_url not in self.seen_urls:
                    self.seen_urls.add(clean_url)
                    # Update article with cleaned URL
                    article['url'] = clean_url
                    self.all_articles.append(article)
                    new_count += 1
                    self.save_counter += 1
                    
                    # Auto-save at interval
                    if self.save_counter >= self.auto_save_interval:
                        self.save_progress()
            
            print(f"✓ Times of India: {new_count} new articles")
            
            # Reset error count on success
            self.error_count = 0
            
        except Exception as e:
            print(f"✗ Times of India error: {str(e)[:50]}")
            self.error_count += 1
        
        return new_count
    
    def _ingest_articles(self, articles: List[Dict]) -> int:
        """Deduplicate against seen_urls, append to batch, trigger auto-save. Returns new count."""
        new_count = 0
        for article in articles:
            if self.cancel_event and self.cancel_event.is_set():
                self.save_progress()
                return new_count
            url = self.text_extractor.clean_url(article.get('url', ''))
            if url and url not in self.seen_urls:
                self.seen_urls.add(url)
                article['url'] = url
                self.all_articles.append(article)
                new_count += 1
                self.save_counter += 1
                if self.save_counter >= self.auto_save_interval:
                    self.save_progress()
        return new_count

    def extract_from_hindu(self, max_articles: int = 200) -> int:
        """Extract from The Hindu RSS - returns count of new articles"""
        print(f"\n{'='*70}")
        print(f"📰 The Hindu Extraction")
        print(f"{'='*70}")
        try:
            articles = self.hindu_extractor.extract(max_articles=max_articles, seen_urls=set(self.seen_urls))
            count = self._ingest_articles(articles)
            print(f"✓ The Hindu: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"✗ The Hindu error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_ndtv(self, max_articles: int = 200) -> int:
        """Extract from NDTV RSS - returns count of new articles"""
        print(f"\n{'='*70}")
        print(f"📰 NDTV Extraction")
        print(f"{'='*70}")
        try:
            articles = self.ndtv_extractor.extract(max_articles=max_articles, seen_urls=set(self.seen_urls))
            count = self._ingest_articles(articles)
            print(f"✓ NDTV: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"✗ NDTV error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_indian_express(self, max_articles: int = 200) -> int:
        """Extract from Indian Express RSS - returns count of new articles"""
        print(f"\n{'='*70}")
        print(f"📰 Indian Express Extraction")
        print(f"{'='*70}")
        try:
            articles = self.indian_express_extractor.extract(max_articles=max_articles, seen_urls=set(self.seen_urls))
            count = self._ingest_articles(articles)
            print(f"✓ Indian Express: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"✗ Indian Express error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_newsdata(self, max_credits: int = 200) -> int:
        """Extract from NewsData.io - returns count of new articles"""
        print(f"\n{'='*70}")
        print(f"📡 NewsData.io Extraction")
        print(f"{'='*70}")
        
        new_count = 0
        
        try:
            # Fetch articles from NewsData.io (uses all 200 credits)
            articles = self.newsdata_extractor.fetch_articles(
                max_credits=max_credits,
                articles_per_credit=10,
                delay_between_calls=1.5
            )
            
            print(f"\n📝 Extracting full text from {len(articles)} articles...")
            
            # Extract full text from URLs
            for i, article in enumerate(articles, 1):
                # Check cancellation
                if self.cancel_event and self.cancel_event.is_set():
                    print(f"\n🛑 Cancellation requested. Saving progress...")
                    self.save_progress()
                    return new_count

                url = article.get('url', '')
                
                # Clean URL using centralized extractor
                clean_url = self.text_extractor.clean_url(url)
                
                if clean_url and clean_url not in self.seen_urls:
                    self.seen_urls.add(clean_url)
                    
                    # Extract full text using centralized extractor
                    try:
                        full_content = self.text_extractor.extract(
                            clean_url,
                            source='NewsData.io',
                            keyword='crime'
                        )
                        
                        # Update article with full text
                        article['url'] = full_content['url']
                        article['title'] = full_content['title'] or article.get('title', '')
                        article['text'] = full_content['text']
                        article['summary'] = full_content['summary']
                        article['full_text_extracted'] = full_content['full_text_extracted']
                        article['extracted_at'] = full_content['extracted_at']
                        
                    except Exception as e:
                        # Keep original data if extraction fails
                        article['text'] = article.get('description', '')
                        article['full_text_extracted'] = False
                    
                    self.all_articles.append(article)
                    new_count += 1
                    self.save_counter += 1
                    
                    # Auto-save at interval with explicit message
                    if self.save_counter >= self.auto_save_interval:
                        print(f"\n💾 Auto-saving at {new_count} articles...")
                        self.save_progress()
                        print(f"✓ Saved successfully. Continuing extraction...\n")
                    
                    # Progress indicator
                    if i % 100 == 0:
                        print(f"  Progress: {i}/{len(articles)} processed, {new_count} new")
            
            # Final save
            if self.all_articles:
                print(f"\n💾 Final save: {len(self.all_articles)} articles...")
                self.save_progress()
                print(f"✓ All articles saved to database")
            
            print(f"✓ NewsData.io: {new_count} new articles (skipped {len(articles) - new_count} duplicates)")
            
            # Reset error count on success
            self.error_count = 0
            
        except ValueError as e:
            print(f"✗ NewsData.io configuration error: {e}")
            print(f"  Please set NEWSDATA_API_KEY in backend/.env file")
            self.error_count += 1
        except Exception as e:
            print(f"✗ NewsData.io error: {str(e)[:100]}")
            self.error_count += 1
        
        return new_count
    
    def extract_indefinitely(self, timeout_minutes: int = None) -> Dict:
        """
        Extract articles indefinitely using all methods until timeout or error
        
        Args:
            timeout_minutes: Optional timeout in minutes. None = run forever
            
        Returns:
            Dictionary with extraction statistics
        """
        print(f"\n{'='*70}")
        print(f"🚀 Unified Article Extraction - ALL METHODS")
        print(f"{'='*70}")
        print(f"Auto-save interval: Every {self.auto_save_interval} articles")
        print(f"Timeout: {timeout_minutes} minutes" if timeout_minutes else "Timeout: None (run indefinitely)")
        print(f"Max consecutive errors: {self.max_errors}")
        print(f"Methods: Google News, Times of India, NewsData.io")
        print(f"{'='*70}\n")
        
        # Load previous progress
        self.load_progress()
        
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60 if timeout_minutes else None
        
        # Google News keywords - Delhi focused
        google_news_keywords = [
            "Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft",
            "Delhi assault", "Delhi rape", "Delhi kidnapping", "Delhi burglary",
            "Delhi police arrest", "Delhi gang", "Delhi violence", "Delhi shooting",
            "Delhi stabbing", "Delhi fraud", "Delhi scam", "Delhi loot",
            "New Delhi crime", "New Delhi murder", "New Delhi robbery",
            "NCR crime", "Noida crime", "Gurgaon crime", "Faridabad crime",
            "Dwarka crime", "Rohini crime", "Shahdara crime", "Outer Delhi crime",
        ]
        
        cycle_count = 0
        total_extracted = 0
        
        try:
            while True:
                cycle_count += 1
                cycle_start = len(self.seen_urls)
                
                print(f"\n{'='*70}")
                print(f"🔄 CYCLE {cycle_count}")
                print(f"{'='*70}")
                print(f"Total URLs processed so far: {len(self.seen_urls)}")
                print(f"Consecutive errors: {self.error_count}/{self.max_errors}")
                
                # Check timeout
                if timeout_seconds:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout_seconds:
                        print(f"\n⏱️  Timeout reached ({timeout_minutes} minutes)")
                        break
                    remaining = (timeout_seconds - elapsed) / 60
                    print(f"Time remaining: {remaining:.1f} minutes")
                
                # Check cancellation
                if self.cancel_event and self.cancel_event.is_set():
                    print(f"\n🛑 Cancellation requested. Saving progress...")
                    self.save_progress()
                    break
                
                # Check error threshold
                if self.error_count >= self.max_errors:
                    print(f"\n⚠️  Too many consecutive errors ({self.error_count}). Stopping extraction.")
                    break
                
                # Method 1: Google News
                print(f"\n📍 Method 1/6: Google News")
                gn_count = self.extract_from_google_news(google_news_keywords, max_articles=200)
                total_extracted += gn_count

                # Method 2: Times of India
                print(f"\n📍 Method 2/6: Times of India")
                toi_count = self.extract_from_times_of_india(max_articles=100)
                total_extracted += toi_count

                # Method 3: The Hindu
                print(f"\n📍 Method 3/6: The Hindu")
                hindu_count = self.extract_from_hindu(max_articles=200)
                total_extracted += hindu_count

                # Method 4: NDTV
                print(f"\n📍 Method 4/6: NDTV")
                ndtv_count = self.extract_from_ndtv(max_articles=200)
                total_extracted += ndtv_count

                # Method 5: Indian Express
                print(f"\n📍 Method 5/6: Indian Express")
                ie_count = self.extract_from_indian_express(max_articles=200)
                total_extracted += ie_count

                # Method 6: NewsData.io (only in first cycle)
                if cycle_count == 1:
                    print(f"\n📍 Method 6/6: NewsData.io")
                    nd_count = self.extract_from_newsdata(max_credits=200)
                    total_extracted += nd_count
                else:
                    print(f"\n📍 Method 6/6: NewsData.io (skipped - already used in cycle 1)")
                    nd_count = 0
                
                cycle_new = len(self.seen_urls) - cycle_start
                
                print(f"\n{'='*70}")
                print(f"✓ Cycle {cycle_count} Complete")
                print(f"{'='*70}")
                print(f"New articles this cycle: {cycle_new}")
                print(f"Total URLs processed: {len(self.seen_urls)}")
                print(f"{'='*70}")
                
                # Save progress after each cycle
                self.save_progress()
                
                # Stop if no new articles found in cycle
                if cycle_new == 0:
                    print(f"\n🛑 No new articles found in this cycle. Stopping extraction.")
                    break
                
                # Short break between cycles
                time.sleep(10)
        
        except KeyboardInterrupt:
            print(f"\n\n⚠️  Interrupted by user. Saving progress...")
            self.save_progress()
        
        except Exception as e:
            print(f"\n\n⚠️  Unexpected error: {e}. Saving progress...")
            self.save_progress()
        
        # Final save
        self.save_progress()
        
        elapsed_minutes = (time.time() - start_time) / 60
        
        print(f"\n{'='*70}")
        print(f"🏁 Extraction Complete")
        print(f"{'='*70}")
        print(f"Total cycles: {cycle_count}")
        print(f"Total URLs processed: {len(self.seen_urls)}")
        print(f"Total time: {elapsed_minutes:.1f} minutes")
        print(f"Final error count: {self.error_count}")
        print(f"{'='*70}\n")
        
        return {
            'success': True,
            'cycles': cycle_count,
            'total_urls': len(self.seen_urls),
            'total_extracted': total_extracted,
            'elapsed_minutes': elapsed_minutes,
            'error_count': self.error_count
        }
