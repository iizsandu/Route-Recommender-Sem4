"""
NDTV Extractor — RSS + Web Scrape
RSS  : Cities/Delhi News, India News (~20 entries each)
Scrape: ndtv.com/delhi-news with pagination (Delhi-only URLs)
Delhi-only, crime keyword filtered, 1.5s delay between requests.
"""
import feedparser
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
from article_text_extractor import get_extractor


class NDTVExtractor:
    def __init__(self):
        self.text_extractor = get_extractor()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.crime_keywords = [
            'crime', 'murder', 'robbery', 'theft', 'assault', 'rape', 'kidnapping',
            'arrested', 'held', 'killed', 'dead', 'body', 'attack', 'shot', 'stabbed',
            'police', 'accused', 'victim', 'gang', 'fraud', 'scam', 'burglary', 'loot',
            'violence', 'shoot', 'firing', 'encounter', 'custody', 'detained',
        ]
        self.delhi_keywords = [
            'delhi', 'new delhi', 'ncr', 'noida', 'gurgaon', 'gurugram',
            'faridabad', 'dwarka', 'rohini',
        ]
        self.rss_feeds = [
            ("NDTV - Delhi/Cities", "https://feeds.feedburner.com/ndtvnews-cities-news"),
            ("NDTV - India",        "https://feeds.feedburner.com/ndtvnews-india-news"),
        ]
        self.scrape_base_url = "https://www.ndtv.com/delhi-news?page={page}"
        self.max_pages = 5

    def _is_crime_related(self, title: str) -> bool:
        return any(kw in title.lower() for kw in self.crime_keywords)

    def _is_delhi_related(self, title: str, url: str) -> bool:
        text = (title + ' ' + url).lower()
        return any(kw in text for kw in self.delhi_keywords)

    def _build_article(self, url: str, fallback_title: str = '') -> Dict:
        result = self.text_extractor.extract(url, source='NDTV')
        return {
            'url': result['url'],
            'title': result['title'] or fallback_title,
            'date': result['publish_date'],
            'text': result['text'],
            'summary': result['summary'],
            'source': 'NDTV',
            'extracted_at': result['extracted_at'],
            'full_text_extracted': result['full_text_extracted'],
        }

    # ── Method 1: RSS ─────────────────────────────────────────────────────────

    def extract_from_rss(self, max_articles: int, seen_urls: set) -> List[Dict]:
        articles = []
        print(f"\n  📡 RSS extraction (max {max_articles})")

        for feed_name, feed_url in self.rss_feeds:
            if len(articles) >= max_articles:
                break
            print(f"  Feed: {feed_name}")
            try:
                feed = feedparser.parse(feed_url)
                print(f"    {len(feed.entries)} entries found")
                for entry in feed.entries:
                    if len(articles) >= max_articles:
                        break
                    title = entry.get('title', '')
                    url = entry.get('link', '')
                    if not url or url in seen_urls:
                        continue
                    if not self._is_crime_related(title):
                        continue
                    if not self._is_delhi_related(title, url):
                        continue
                    seen_urls.add(url)
                    print(f"    Extracting: {url[:80]}...")
                    articles.append(self._build_article(url, title))
                    time.sleep(1.5)
            except Exception as e:
                print(f"    RSS error ({feed_name}): {e}")

        print(f"  ✓ RSS: {len(articles)} articles")
        return articles

    # ── Method 2: Web Scrape ──────────────────────────────────────────────────

    def extract_from_web(self, max_articles: int, seen_urls: set) -> List[Dict]:
        articles = []
        print(f"\n  🌐 Web scrape extraction (max {max_articles})")

        for page in range(1, self.max_pages + 1):
            if len(articles) >= max_articles:
                break
            url = self.scrape_base_url.format(page=page)
            print(f"  Page {page}: {url}")
            try:
                resp = requests.get(url, headers=self.headers, timeout=15)
                if resp.status_code != 200:
                    print(f"    HTTP {resp.status_code} — stopping pagination")
                    break
                soup = BeautifulSoup(resp.text, 'html.parser')

                all_delhi = 0
                skipped_seen = 0
                skipped_crime = 0
                page_links = []

                for a in soup.find_all('a', href=True):
                    href = a['href']
                    title = a.get_text(strip=True)
                    if 'ndtv.com/delhi-news/' not in href:
                        continue
                    if not href.startswith('http'):
                        href = 'https://www.ndtv.com' + href
                    all_delhi += 1
                    if href in seen_urls:
                        skipped_seen += 1
                        continue
                    if not title:
                        continue
                    if not self._is_crime_related(title):
                        skipped_crime += 1
                        continue
                    page_links.append((href, title))

                print(f"    Delhi links: {all_delhi} | already seen: {skipped_seen} | not crime: {skipped_crime} | new crime: {len(page_links)}")

                seen_page = set()
                for href, title in page_links:
                    if href in seen_page:
                        continue
                    seen_page.add(href)
                    if len(articles) >= max_articles:
                        break
                    seen_urls.add(href)
                    print(f"    Extracting: {href[:80]}...")
                    articles.append(self._build_article(href, title))
                    time.sleep(1.5)

                time.sleep(2)
            except Exception as e:
                print(f"    Scrape error (page {page}): {e}")
                break

        print(f"  ✓ Web scrape: {len(articles)} articles")
        return articles

    # ── Combined ──────────────────────────────────────────────────────────────

    def extract(self, max_articles: int = 200, seen_urls: set = None) -> List[Dict]:
        if seen_urls is None:
            seen_urls = set()
        all_articles = []

        print(f"\n{'='*60}")
        print(f"📰 NDTV Extraction (max {max_articles})")
        print(f"{'='*60}")

        rss_articles = self.extract_from_rss(max_articles, seen_urls)
        all_articles.extend(rss_articles)

        remaining = max_articles - len(all_articles)
        if remaining > 0:
            web_articles = self.extract_from_web(remaining, seen_urls)
            all_articles.extend(web_articles)

        text_ok = sum(1 for a in all_articles if a.get('full_text_extracted'))
        print(f"\n{'='*60}")
        print(f"✓ NDTV Total  : {len(all_articles)} articles")
        print(f"✓ Text found  : {text_ok}/{len(all_articles)}")
        print(f"{'='*60}")
        return all_articles
