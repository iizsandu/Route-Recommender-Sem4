"""
NewsData.io Article Extractor
Free tier limits:
  - 200 credits / 24 hours  (daily budget)
  - 30 requests / 15 minutes (rate window)
Automatically waits out the 15-min window when exhausted, then resumes.
"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from newsdata_credit_manager import credit_manager
import os
from dotenv import load_dotenv

load_dotenv()


class NewsDataExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NEWSDATA_API_KEY')
        if not self.api_key:
            raise ValueError("NewsData.io API key not found. Set NEWSDATA_API_KEY in .env")

        self.base_url = "https://newsdata.io/api/1/latest"

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
        delay_between_calls: float = 1.5,
    ) -> List[Dict]:
        """
        Fetch articles from NewsData.io.
        Respects both the daily budget and the 30 req/15 min window.
        Automatically sleeps when the window is full and resumes after.
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
