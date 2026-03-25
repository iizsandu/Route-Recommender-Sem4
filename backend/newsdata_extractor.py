"""
NewsData.io Article Extractor
Free tier limits:
  - 200 credits / 24 hours  (daily budget)
  - 30 requests / 15 minutes (rate window)
Automatically waits out the 15-min window when exhausted, then resumes.
fetch_metadata() fetches article stubs from the API.
extract() fetches metadata then pulls full text for each article — same contract as all other extractors.
"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from newsdata_credit_manager import credit_manager
from article_text_extractor import get_extractor
import os
from dotenv import load_dotenv

load_dotenv()


class NewsDataExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NEWSDATA_API_KEY')
        if not self.api_key:
            raise ValueError("NewsData.io API key not found. Set NEWSDATA_API_KEY in .env")

        self.base_url = "https://newsdata.io/api/1/latest"
        self.text_extractor = get_extractor()

        self.keywords = [
            "Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft",
            "Delhi assault", "Delhi kidnapping", "Delhi rape", "Delhi burglary",
            "Delhi shooting", "Delhi stabbing", "Delhi gang", "Delhi fraud",
            "Delhi police arrest", "Delhi violence", "Delhi loot",
            "New Delhi crime", "NCR crime", "Noida crime", "Gurgaon crime",
        ]

    def fetch_metadata(
        self,
        max_credits: int = 200,
        articles_per_credit: int = 10,
        delay_between_calls: float = 1.5,
    ) -> List[Dict]:
        """
        Fetch article stubs (metadata only, no full text) from NewsData.io API.
        Respects both the daily budget and the 30 req/15 min window.
        Automatically sleeps when the window is full and resumes after.
        Returns articles with full_text_extracted=False — call extract() to get full text.
        """
        status = credit_manager.print_status()

        if not status['credits_remaining']:
            print(f"  No daily credits left. Reset in {status['hours_until_reset']}h {status['minutes_until_reset']}m")
            return []

        # Cap to available daily credits
        max_credits = min(max_credits, status['credits_remaining'])

        print(f"\n  NewsData.io Extraction")
        print(f"  Daily credits to use : {max_credits} (of {status['credits_remaining']} available)")
        print(f"  Window limit         : {status['window_max']} req / 15 min")
        print(f"  Target articles      : ~{max_credits * articles_per_credit}")

        all_articles = []
        seen_urls = set()
        credits_used = 0
        keyword_index = 0

        while credits_used < max_credits:
            # ── Ask credit manager for permission ──────────────────────────
            result = credit_manager.use_credit()

            if not result['allowed']:
                if result['reason'] == 'daily_exhausted':
                    print(f"  Daily credit budget exhausted after {credits_used} calls.")
                    break

                if result['reason'] == 'window_full':
                    wait = result['wait_seconds']
                    m, s = divmod(wait, 60)
                    print(f"\n  Rate window full (30/30). Waiting {m}m {s}s for window reset...")
                    time.sleep(wait)
                    print(f"  Window reset — resuming extraction.")
                    continue  # retry the same credit slot

            # ── Fire the API call ──────────────────────────────────────────
            keyword = self.keywords[keyword_index % len(self.keywords)]
            keyword_index += 1
            credits_used += 1

            print(f"  [{credits_used}/{max_credits}] keyword: '{keyword}'")

            try:
                params = {
                    'apikey': self.api_key,
                    'q': keyword,
                    'language': 'en',
                    'country': 'in',
                    'size': articles_per_credit,
                }
                resp = requests.get(self.base_url, params=params, timeout=30)

                if resp.status_code == 403:
                    print(f"  403 Forbidden — check API key at newsdata.io/dashboard")
                    break

                if resp.status_code == 429:
                    # Server-side rate limit (shouldn't happen if manager is correct)
                    print(f"  429 from server — waiting 60s...")
                    time.sleep(60)
                    credits_used -= 1  # don't count this as a used credit
                    continue

                if resp.status_code != 200:
                    print(f"  HTTP {resp.status_code} — skipping")
                    continue

                data = resp.json()
                if data.get('status') != 'success':
                    print(f"  API error: {data.get('message', 'unknown')}")
                    break

                results = data.get('results', [])
                new_count = 0
                for item in results:
                    url = item.get('link')
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    all_articles.append({
                        'title': item.get('title', ''),
                        'url': url,
                        'source': 'NewsData.io',
                        'published_date': item.get('pubDate', ''),
                        'description': item.get('description', ''),
                        'extracted_at': datetime.now().isoformat(),
                        'full_text_extracted': False,
                    })
                    new_count += 1

                print(f"    +{new_count} articles  (total: {len(all_articles)})")

            except requests.exceptions.Timeout:
                print(f"  Timeout — skipping")
                continue
            except Exception as e:
                print(f"  Error: {e}")
                continue

            # Small delay between calls within the same window
            if credits_used < max_credits:
                time.sleep(delay_between_calls)

        final = credit_manager.print_status()
        print(f"\n  NewsData.io done — {credits_used} credits used, {len(all_articles)} articles fetched")
        return all_articles

    def extract(
        self,
        max_credits: int = 200,
        articles_per_credit: int = 10,
        delay_between_calls: float = 1.5,
        seen_urls: set = None,
    ) -> List[Dict]:
        """
        Full extraction: fetch metadata from API, then pull full text for each article.
        Same contract as all other extractors — returns fully populated articles.
        Articles where text extraction fails are still returned with full_text_extracted=False
        so _ingest_articles() can filter them uniformly.
        """
        if seen_urls is None:
            seen_urls = set()

        stubs = self.fetch_metadata(
            max_credits=max_credits,
            articles_per_credit=articles_per_credit,
            delay_between_calls=delay_between_calls,
        )

        print(f"\n  Extracting full text from {len(stubs)} NewsData.io articles...")
        articles = []

        for i, stub in enumerate(stubs, 1):
            url = self.text_extractor.clean_url(stub.get('url', ''))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                full_content = self.text_extractor.extract(url, source='NewsData.io', keyword='crime')
                stub['url'] = full_content['url']
                stub['title'] = full_content['title'] or stub.get('title', '')
                stub['text'] = full_content['text']
                stub['summary'] = full_content['summary']
                stub['full_text_extracted'] = full_content['full_text_extracted']
                stub['extracted_at'] = full_content['extracted_at']
            except Exception:
                stub['text'] = stub.get('description', '')
                stub['full_text_extracted'] = False

            articles.append(stub)

            if i % 100 == 0:
                print(f"  Progress: {i}/{len(stubs)} processed")

        text_ok = sum(1 for a in articles if a.get('full_text_extracted'))
        print(f"\n{'='*60}")
        print(f"✓ NewsData.io Total : {len(articles)} articles")
        print(f"✓ Text found        : {text_ok}/{len(articles)}")
        print(f"{'='*60}")
        return articles
