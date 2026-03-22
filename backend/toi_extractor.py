"""
Times of India Article Extractor
Two-method approach:
  1. RSS feeds  — fast, reliable, direct URLs (Delhi News + India News)
  2. Web scrape — crawls TOI Delhi/crime topic pages, paginates until no new crime links or HTTP error
Both methods filter by crime keywords and deduplicate by URL. No article cap.
"""
import requests
import feedparser
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
            'police', 'accused', 'victim', 'gang', 'fraud', 'scam', 'burglary', 'loot',
            'violence', 'shoot', 'firing', 'encounter', 'custody', 'detained', 'arrested'
        ]
        self.rss_feeds = [
            ("Delhi News",  "https://timesofindia.indiatimes.com/rssfeeds/-2128839596.cms"),
            ("India News",  "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms"),
        ]
        self.toi_delhi_urls = [
            "https://timesofindia.indiatimes.com/city/delhi",
            "https://timesofindia.indiatimes.com/topic/delhi-crime",
            "https://timesofindia.indiatimes.com/topic/delhi-police",
            "https://timesofindia.indiatimes.com/topic/delhi-murder",
        ]
        self.text_extractor = get_extractor()

    def _is_crime_related(self, title: str) -> bool:
        return any(kw in title.lower() for kw in self.crime_keywords)

    def _build_article(self, url: str, fallback_title: str = '') -> Dict:
        result = self.text_extractor.extract(url, source='Times of India')
        return {
            'url': result['url'],
            'title': result['title'] or fallback_title,
            'date': result['publish_date'],
            'text': result['text'],
            'summary': result['summary'],
            'source': 'Times of India',
            'extracted_at': result['extracted_at'],
            'description': '',
            'full_text_extracted': result['full_text_extracted']
        }

    # ── Method 1: RSS ─────────────────────────────────────────────────────────

    def extract_from_rss(self, seen_urls: set = None) -> List[Dict]:
        """Extract all crime articles from TOI RSS feeds (naturally bounded by feed size)."""
        if seen_urls is None:
            seen_urls = set()
        articles = []

        print(f"\n  📡 RSS extraction")

        for feed_name, feed_url in self.rss_feeds:
            print(f"  Feed: {feed_name}")
            try:
                feed = feedparser.parse(feed_url)
                entries = feed.entries
                print(f"    {len(entries)} entries found")

                for entry in entries:
                    title = entry.get('title', '')
                    url = entry.get('link', '')

                    if not url or url in seen_urls:
                        continue
                    if not self._is_crime_related(title):
                        continue

                    seen_urls.add(url)
                    print(f"    Extracting: {url[:80]}...")
                    article = self._build_article(url, fallback_title=title)
                    articles.append(article)
                    time.sleep(0.3)

            except Exception as e:
                print(f"    RSS error ({feed_name}): {e}")

        print(f"  ✓ RSS: {len(articles)} articles extracted")
        return articles

    # ── Method 2: Web Scrape ──────────────────────────────────────────────────

    def extract_from_web(self, seen_urls: set = None) -> List[Dict]:
        """Scrape TOI Delhi/crime pages. Stops when no new crime links found or HTTP error."""
        if seen_urls is None:
            seen_urls = set()
        articles = []

        print(f"\n  🌐 Web scrape extraction")

        for page_url in self.toi_delhi_urls:
            print(f"  Page: {page_url}")
            try:
                response = requests.get(page_url, headers=self.headers, timeout=10)
                if response.status_code == 429:
                    print(f"    ⚠️  Rate limited (429) — stopping web scrape")
                    return articles
                if response.status_code != 200:
                    print(f"    ✗ HTTP {response.status_code} — skipping")
                    continue

                soup = BeautifulSoup(response.content, 'html.parser')
                page_links = []

                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    title = link.get_text(strip=True)

                    if not href or not title:
                        continue
                    if not self._is_crime_related(title):
                        continue

                    full_url = href if href.startswith('http') else f"https://timesofindia.indiatimes.com{href}"

                    if full_url in seen_urls:
                        continue
                    if self.text_extractor.is_video_url(full_url):
                        continue
                    page_links.append((full_url, title))

                print(f"    New crime links: {len(page_links)}")
                if not page_links:
                    continue

                for full_url, title in page_links:
                    seen_urls.add(full_url)
                    print(f"    Extracting: {full_url[:80]}...")
                    article = self._build_article(full_url, fallback_title=title)
                    articles.append(article)
                    time.sleep(0.5)

            except Exception as e:
                print(f"    Scrape error ({page_url}): {e}")

        print(f"  ✓ Web scrape: {len(articles)} articles extracted")
        return articles

    # ── Combined ──────────────────────────────────────────────────────────────

    def extract_from_times_of_india(self) -> List[Dict]:
        """
        Run RSS first, then web scrape for additional articles.
        Shared seen_urls set ensures no duplicates across both methods.
        No article cap — runs until exhausted or rate-limited.
        """
        print(f"\n{'='*60}")
        print(f"📰 Times of India Extraction")
        print(f"{'='*60}")

        seen_urls = set()
        all_articles = []

        rss_articles = self.extract_from_rss(seen_urls=seen_urls)
        all_articles.extend(rss_articles)

        web_articles = self.extract_from_web(seen_urls=seen_urls)
        all_articles.extend(web_articles)

        text_ok = sum(1 for a in all_articles if a.get('full_text_extracted'))
        print(f"\n{'='*60}")
        print(f"✓ TOI Total  : {len(all_articles)} articles")
        print(f"✓ Text found : {text_ok}/{len(all_articles)}")
        print(f"{'='*60}")

        return all_articles

    def extract_articles(self, sources: List[str] = None) -> List[Dict]:
        if not sources:
            sources = ['times_of_india']
        all_articles = []
        if 'times_of_india' in sources:
            all_articles.extend(self.extract_from_times_of_india())
        return all_articles
