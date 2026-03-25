"""
Unified Article Extractor
Combines all extraction methods and runs indefinitely until timeout/error.
Only saves articles where full_text_extracted is True.
Tracks per-source counts and prints a summary at the end.
"""
from google_news_extractor import GoogleNewsExtractor
from toi_extractor import ArticleExtractor
from newsdata_extractor import NewsDataExtractor
from hindu_extractor import HinduExtractor
from ndtv_extractor import NDTVExtractor
from indian_express_extractor import IndianExpressExtractor
from newsapi_extractor import NewsAPIExtractor
from db_handler import DBHandler
from datetime import datetime
import time
import json
import os
from typing import List, Dict


_TRACKING_PARAMS = [
    '&ved=', '&usg=', '&sa=', '&source=', '&cd=', '&cad=',
    '&utm_source=', '&utm_medium=', '&utm_campaign=',
    '&fbclid=', '&gclid='
]


def _clean_url(url: str) -> str:
    if not url:
        return url
    for param in _TRACKING_PARAMS:
        if param in url:
            url = url.split(param)[0]
    return url


class UnifiedExtractor:
    def __init__(self, auto_save_interval: int = 50, cancel_event=None):
        self.google_news_extractor = GoogleNewsExtractor()
        self.times_of_india_extractor = ArticleExtractor()
        self.newsdata_extractor = NewsDataExtractor()
        self.hindu_extractor = HinduExtractor()
        self.ndtv_extractor = NDTVExtractor()
        self.indian_express_extractor = IndianExpressExtractor()
        self.newsapi_extractor = NewsAPIExtractor()
        self.auto_save_interval = auto_save_interval
        self.cancel_event = cancel_event
        self.all_articles = []
        self.seen_urls = set()
        self.save_counter = 0
        self.progress_file = "extraction_progress.json"
        self.error_count = 0
        self.max_errors = 10
        # Per-source article counts (this session only)
        self.source_counts = {
            'Google News': 0,
            'Times of India': 0,
            'The Hindu': 0,
            'NDTV': 0,
            'Indian Express': 0,
            'NewsData.io': 0,
            'NewsAPI.org': 0,
        }
        # Persistent DB connection — created once, reused for all saves
        self.db = DBHandler(collection_name="articles2")
        if not self.db.connected:
            print("  WARNING: MongoDB not connected — articles will only be saved to JSON")

    def save_progress(self):
        try:
            data = {
                'articles': self.all_articles,
                'seen_urls': list(self.seen_urls),
                'total_articles': len(self.all_articles),
                'saved_at': datetime.now().isoformat(),
                'error_count': self.error_count
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)

            if self.all_articles and self.db.connected:
                result = self.db.save_articles(self.all_articles)
                print(f"\n  Saved to DB: {result['inserted']} new, {result['duplicates']} duplicates")
                self.all_articles = []
                self.save_counter = 0

            print(f"  Progress saved: {len(self.seen_urls)} total URLs processed")

        except Exception as e:
            print(f"\n  WARNING: Failed to save progress: {e}")

    def load_progress(self) -> bool:
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.all_articles = data.get('articles', [])
                self.seen_urls = set(data.get('seen_urls', []))
                self.error_count = data.get('error_count', 0)
                print(f"\n  Loaded previous progress: {len(self.seen_urls)} URLs processed")
                return True
            except Exception as e:
                print(f"\n  WARNING: Failed to load progress: {e}")
        return False

    def _ingest_articles(self, articles: List[Dict]) -> int:
        """
        Deduplicate against seen_urls, skip articles without extracted text,
        append to batch, trigger auto-save. Returns new count.
        """
        new_count = 0
        skipped_no_text = 0
        for article in articles:
            if self.cancel_event and self.cancel_event.is_set():
                self.save_progress()
                return new_count

            # Only save articles where text was successfully extracted
            if not article.get('full_text_extracted'):
                skipped_no_text += 1
                continue

            url = _clean_url(article.get('url', ''))
            if url and url not in self.seen_urls:
                self.seen_urls.add(url)
                article['url'] = url
                self.all_articles.append(article)
                new_count += 1
                self.save_counter += 1
                # Track per-source count
                source = article.get('source', 'Unknown')
                if source in self.source_counts:
                    self.source_counts[source] += 1
                if self.save_counter >= self.auto_save_interval:
                    self.save_progress()

        if skipped_no_text:
            print(f"  Skipped {skipped_no_text} articles with no extracted text")
        return new_count

    def _print_summary(self, elapsed_minutes: float = None):
        """Print a formatted per-source breakdown to terminal."""
        total = sum(self.source_counts.values())
        print(f"\n{'='*60}")
        print(f"  EXTRACTION SUMMARY")
        print(f"{'='*60}")
        for source, count in self.source_counts.items():
            bar = '#' * min(count, 40)
            print(f"  {source:<22} {count:>4}  {bar}")
        print(f"  {'-'*50}")
        print(f"  {'TOTAL':<22} {total:>4}")
        if elapsed_minutes is not None:
            print(f"  Time elapsed: {elapsed_minutes:.1f} minutes")
        print(f"{'='*60}\n")

    # ── Per-source extract methods ─────────────────────────────────────────────

    def extract_from_google_news(self, keywords: List[str]) -> int:
        if self.cancel_event and self.cancel_event.is_set():
            return 0
        try:
            articles = self.google_news_extractor.extract(
                keywords=keywords,
                seen_urls=set(self.seen_urls)
            )
            count = self._ingest_articles(articles)
            print(f"  Google News: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"  Google News error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_times_of_india(self) -> int:
        print(f"\n{'='*70}")
        print(f"  Times of India Extraction")
        print(f"{'='*70}")
        try:
            articles = self.times_of_india_extractor.extract_from_times_of_india()
            count = self._ingest_articles(articles)
            print(f"  Times of India: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"  Times of India error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_hindu(self) -> int:
        print(f"\n{'='*70}")
        print(f"  The Hindu Extraction")
        print(f"{'='*70}")
        try:
            articles = self.hindu_extractor.extract(seen_urls=set(self.seen_urls))
            count = self._ingest_articles(articles)
            print(f"  The Hindu: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"  The Hindu error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_ndtv(self) -> int:
        print(f"\n{'='*70}")
        print(f"  NDTV Extraction")
        print(f"{'='*70}")
        try:
            articles = self.ndtv_extractor.extract(seen_urls=set(self.seen_urls))
            count = self._ingest_articles(articles)
            print(f"  NDTV: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"  NDTV error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_indian_express(self) -> int:
        print(f"\n{'='*70}")
        print(f"  Indian Express Extraction")
        print(f"{'='*70}")
        try:
            articles = self.indian_express_extractor.extract(seen_urls=set(self.seen_urls))
            count = self._ingest_articles(articles)
            print(f"  Indian Express: {count} new articles")
            self.error_count = 0
            return count
        except Exception as e:
            print(f"  Indian Express error: {str(e)[:80]}")
            self.error_count += 1
            return 0

    def extract_from_newsapi(self, max_requests: int = 100) -> int:
        print(f"\n{'='*70}")
        print(f"  NewsAPI.org Extraction")
        print(f"{'='*70}")
        try:
            articles = self.newsapi_extractor.extract(
                max_requests=max_requests,
                delay_between_calls=1.0,
                seen_urls=set(self.seen_urls),
            )
            count = self._ingest_articles(articles)
            print(f"  NewsAPI.org: {count} new articles")
            self.error_count = 0
            return count
        except ValueError as e:
            print(f"  NewsAPI.org configuration error: {e}")
            self.error_count += 1
            return 0
        except Exception as e:
            print(f"  NewsAPI.org error: {str(e)[:100]}")
            self.error_count += 1
            return 0

    def extract_from_newsdata(self, max_credits: int = 200) -> int:
        print(f"\n{'='*70}")
        print(f"  NewsData.io Extraction")
        print(f"{'='*70}")
        try:
            articles = self.newsdata_extractor.extract(
                max_credits=max_credits,
                articles_per_credit=10,
                delay_between_calls=1.5,
                seen_urls=set(self.seen_urls),
            )
            count = self._ingest_articles(articles)
            print(f"  NewsData.io: {count} new articles")
            self.error_count = 0
            return count
        except ValueError as e:
            print(f"  NewsData.io configuration error: {e}")
            self.error_count += 1
            return 0
        except Exception as e:
            print(f"  NewsData.io error: {str(e)[:100]}")
            self.error_count += 1
            return 0

    # ── Main loop ──────────────────────────────────────────────────────────────

    def extract_indefinitely(self, timeout_minutes: int = None) -> Dict:
        print(f"\n{'='*70}")
        print(f"  Unified Article Extraction - ALL METHODS")
        print(f"{'='*70}")
        print(f"  Auto-save interval : Every {self.auto_save_interval} articles")
        print(f"  Timeout            : {timeout_minutes} minutes" if timeout_minutes else "  Timeout            : None (run indefinitely)")
        print(f"  Max errors         : {self.max_errors}")
        print(f"  Text-only saving   : YES")
        print(f"{'='*70}\n")

        self.load_progress()

        start_time = time.time()
        timeout_seconds = timeout_minutes * 60 if timeout_minutes else None

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
                print(f"  CYCLE {cycle_count}")
                print(f"{'='*70}")
                print(f"  Total URLs processed so far: {len(self.seen_urls)}")
                print(f"  Consecutive errors: {self.error_count}/{self.max_errors}")

                if timeout_seconds:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout_seconds:
                        print(f"\n  Timeout reached ({timeout_minutes} minutes)")
                        break
                    remaining = (timeout_seconds - elapsed) / 60
                    print(f"  Time remaining: {remaining:.1f} minutes")

                if self.cancel_event and self.cancel_event.is_set():
                    print(f"\n  Cancellation requested. Saving progress...")
                    self.save_progress()
                    break

                if self.error_count >= self.max_errors:
                    print(f"\n  Too many consecutive errors ({self.error_count}). Stopping.")
                    break

                print(f"\n  [1/7] Google News")
                total_extracted += self.extract_from_google_news(google_news_keywords)

                print(f"\n  [2/7] Times of India")
                total_extracted += self.extract_from_times_of_india()

                print(f"\n  [3/7] The Hindu")
                total_extracted += self.extract_from_hindu()

                print(f"\n  [4/7] NDTV")
                total_extracted += self.extract_from_ndtv()

                print(f"\n  [5/7] Indian Express")
                total_extracted += self.extract_from_indian_express()

                if cycle_count == 1:
                    print(f"\n  [6/7] NewsData.io")
                    total_extracted += self.extract_from_newsdata(max_credits=200)
                else:
                    print(f"\n  [6/7] NewsData.io (skipped - already used in cycle 1)")

                if cycle_count == 1:
                    print(f"\n  [7/7] NewsAPI.org")
                    total_extracted += self.extract_from_newsapi(max_requests=100)
                else:
                    print(f"\n  [7/7] NewsAPI.org (skipped - already used in cycle 1)")

                cycle_new = len(self.seen_urls) - cycle_start

                print(f"\n  Cycle {cycle_count} complete — {cycle_new} new articles this cycle")

                self.save_progress()

                if cycle_new == 0:
                    print(f"\n  No new articles found in this cycle. Stopping.")
                    break

                time.sleep(10)

        except KeyboardInterrupt:
            print(f"\n  Interrupted by user. Saving progress...")
            self.save_progress()
        except Exception as e:
            print(f"\n  Unexpected error: {e}. Saving progress...")
            self.save_progress()

        self.save_progress()

        elapsed_minutes = (time.time() - start_time) / 60

        # Print terminal summary
        self._print_summary(elapsed_minutes)

        print(f"\n{'='*70}")
        print(f"  Extraction Complete")
        print(f"{'='*70}")
        print(f"  Total cycles        : {cycle_count}")
        print(f"  Total URLs processed: {len(self.seen_urls)}")
        print(f"  Total time          : {elapsed_minutes:.1f} minutes")
        print(f"  Error count         : {self.error_count}")
        print(f"{'='*70}\n")

        return {
            'success': True,
            'cycles': cycle_count,
            'total_urls': len(self.seen_urls),
            'total_extracted': total_extracted,
            'elapsed_minutes': round(elapsed_minutes, 1),
            'error_count': self.error_count,
            'source_breakdown': dict(self.source_counts),
        }
