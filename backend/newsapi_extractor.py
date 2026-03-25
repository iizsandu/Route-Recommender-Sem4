"""
NewsAPI.org Article Extractor
Free Developer plan limits:
  - 100 requests / 24 hours
  - 100 articles per request (pageSize max)
  - Page 1 only on free tier (no deep pagination)
  - Date range supported via from_param / to params
  - Only /v2/everything used (supports date range + keyword search)

fetch_metadata() — hits the API, returns article stubs (no full text).
extract()        — calls fetch_metadata() then pulls full text for each URL.
                   Same contract as all other extractors.
"""
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional
from newsapi_request_manager import newsapi_request_manager
from article_text_extractor import get_extractor
import os
from dotenv import load_dotenv

load_dotenv()


class NewsAPIExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NEWSAPI_API_KEY')
        if not self.api_key:
            raise ValueError("NewsAPI.org API key not found. Set NEWSAPI_API_KEY in .env")

        self.base_url = "https://newsapi.org/v2/everything"
        self.text_extractor = get_extractor()

        # Delhi crime keywords — each becomes one API request
        self.keywords = [
            "Delhi crime",
            "Delhi murder",
            "Delhi robbery theft",
            "Delhi assault rape",
            "Delhi kidnapping",
            "Delhi police arrested",
            "Delhi gang violence",
            "Delhi fraud scam",
            "Delhi shooting stabbing",
            "New Delhi crime",
            "Noida crime",
            "Gurgaon crime",
        ]

        self.crime_keywords = [
            'crime', 'murder', 'robbery', 'theft', 'assault', 'rape', 'kidnapping',
            'arrested', 'held', 'killed', 'dead', 'body', 'attack', 'shot', 'stabbed',
            'police', 'accused', 'victim', 'gang', 'fraud', 'scam', 'burglary', 'loot',
            'violence', 'shoot', 'firing', 'encounter', 'custody', 'detained',
        ]

    def _is_crime_related(self, title: str, description: str = '') -> bool:
        text = (title + ' ' + description).lower()
        return any(kw in text for kw in self.crime_keywords)

    def fetch_metadata(
        self,
        max_requests: int = 100,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        delay_between_calls: float = 1.0,
    ) -> List[Dict]:
        """
        Fetch article stubs from NewsAPI.org /v2/everything.
        - max_requests: cap on API calls (each = 1 daily request)
        - from_date / to_date: ISO date strings 'YYYY-MM-DD' (optional)
        - Free tier: pageSize=100, page=1 only
        Returns stubs with full_text_extracted=False.
        """
        status = newsapi_request_manager.print_status()

        if not status['can_use']:
            print(f"  No daily requests left. Reset in "
                  f"{status['hours_until_reset']}h {status['minutes_until_reset']}m")
            return []

        max_requests = min(max_requests, status['requests_remaining'])

        print(f"\n  NewsAPI.org Extraction")
        print(f"  Daily requests to use : {max_requests} (of {status['requests_remaining']} available)")
        print(f"  Articles per request  : {status['articles_per_request']}")
        if from_date:
            print(f"  Date range            : {from_date} → {to_date or 'now'}")

        all_articles = []
        seen_urls = set()
        requests_used = 0

        for keyword in self.keywords:
            if requests_used >= max_requests:
                print(f"  Request cap reached ({max_requests}) — stopping")
                break

            result = newsapi_request_manager.use_request()
            if not result['allowed']:
                print(f"  Daily request budget exhausted after {requests_used} calls.")
                break

            requests_used += 1
            print(f"  [{requests_used}/{max_requests}] keyword: '{keyword}'")

            try:
                params = {
                    'apiKey': self.api_key,
                    'q': keyword,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 100,   # max on free tier
                    'page': 1,         # free tier: page 1 only
                }
                if from_date:
                    params['from'] = from_date
                if to_date:
                    params['to'] = to_date

                resp = requests.get(self.base_url, params=params, timeout=30)

                if resp.status_code == 401:
                    print(f"  401 Unauthorized — check NEWSAPI_API_KEY in .env")
                    break

                if resp.status_code == 426:
                    print(f"  426 Upgrade Required — this endpoint requires a paid plan")
                    break

                if resp.status_code == 429:
                    print(f"  429 Rate limited — waiting 60s...")
                    time.sleep(60)
                    # refund the request slot
                    requests_used -= 1
                    continue

                if resp.status_code != 200:
                    print(f"  HTTP {resp.status_code} — skipping keyword '{keyword}'")
                    continue

                data = resp.json()
                if data.get('status') != 'ok':
                    print(f"  API error: {data.get('message', 'unknown')}")
                    # If it's a plan restriction error, stop entirely
                    if 'upgrade' in data.get('message', '').lower():
                        print(f"  Plan restriction — stopping NewsAPI extraction")
                        break
                    continue

                articles_raw = data.get('articles', [])
                new_count = 0

                for item in articles_raw:
                    url = item.get('url', '')
                    title = item.get('title', '') or ''
                    description = item.get('description', '') or ''

                    if not url or url in seen_urls:
                        continue
                    if url == 'https://removed.com' or title == '[Removed]':
                        continue
                    if not self._is_crime_related(title, description):
                        continue
                    if self.text_extractor.is_video_url(url):
                        continue

                    seen_urls.add(url)
                    all_articles.append({
                        'title': title,
                        'url': url,
                        'source': 'NewsAPI.org',
                        'published_date': item.get('publishedAt', ''),
                        'date': item.get('publishedAt', '')[:10] if item.get('publishedAt') else '',
                        'description': description,
                        'extracted_at': datetime.now().isoformat(),
                        'full_text_extracted': False,
                    })
                    new_count += 1

                total_available = data.get('totalResults', 0)
                print(f"    +{new_count} articles  (total so far: {len(all_articles)}, "
                      f"API reports {total_available} total available)")

            except requests.exceptions.Timeout:
                print(f"  Timeout on '{keyword}' — skipping")
                continue
            except Exception as e:
                print(f"  Error on '{keyword}': {e}")
                continue

            if requests_used < max_requests:
                time.sleep(delay_between_calls)

        final = newsapi_request_manager.print_status()
        print(f"\n  NewsAPI.org done — {requests_used} requests used, {len(all_articles)} stubs fetched")
        return all_articles

    def extract(
        self,
        max_requests: int = 100,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        delay_between_calls: float = 1.0,
        seen_urls: set = None,
    ) -> List[Dict]:
        """
        Full extraction: fetch metadata then pull full text for each article.
        Same contract as all other extractors.
        """
        if seen_urls is None:
            seen_urls = set()

        stubs = self.fetch_metadata(
            max_requests=max_requests,
            from_date=from_date,
            to_date=to_date,
            delay_between_calls=delay_between_calls,
        )

        print(f"\n  Extracting full text from {len(stubs)} NewsAPI.org articles...")
        articles = []

        for i, stub in enumerate(stubs, 1):
            url = self.text_extractor.clean_url(stub.get('url', ''))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                full_content = self.text_extractor.extract(url, source='NewsAPI.org', keyword='crime')
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

            if i % 50 == 0:
                print(f"  Progress: {i}/{len(stubs)} processed")

        text_ok = sum(1 for a in articles if a.get('full_text_extracted'))
        print(f"\n{'='*60}")
        print(f"✓ NewsAPI.org Total : {len(articles)} articles")
        print(f"✓ Text found        : {text_ok}/{len(articles)}")
        print(f"{'='*60}")
        return articles
