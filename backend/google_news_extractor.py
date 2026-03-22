"""
Google News Extractor — 3-layer approach
Layer 1: Google News RSS (requests + BeautifulSoup XML parse)
Layer 2: googlenewsdecoder resolves CBMi redirect URLs → real article URLs
Layer 3: gnews library as supplementary source (also decoded via Layer 2)
Delhi-only, crime keyword filtered. No article cap — runs until exhausted or rate-limited.
"""
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from typing import List, Dict
import time
from article_text_extractor import get_extractor

try:
    from googlenewsdecoder import gnewsdecoder
    _DECODER_AVAILABLE = True
except ImportError:
    _DECODER_AVAILABLE = False
    print("  ⚠️  googlenewsdecoder not installed — Google News URLs will fail")

try:
    from gnews import GNews
    _GNEWS_AVAILABLE = True
except ImportError:
    _GNEWS_AVAILABLE = False


class GoogleNewsExtractor:
    def __init__(self):
        self.text_extractor = get_extractor()
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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

    def _is_crime_related(self, title: str) -> bool:
        return any(kw in title.lower() for kw in self.crime_keywords)

    def _is_delhi_related(self, title: str, url: str = '') -> bool:
        text = (title + ' ' + url).lower()
        return any(kw in text for kw in self.delhi_keywords)

    def _decode_google_url(self, google_url: str) -> str:
        """Resolve a CBMi... Google News redirect to the real article URL."""
        if not _DECODER_AVAILABLE:
            return None
        if 'news.google.com' not in google_url:
            return google_url  # already a real URL
        try:
            result = gnewsdecoder(google_url, interval=1)
            if result.get('status'):
                real_url = result['decoded_url']
                if 'news.google.com' not in real_url:
                    return real_url
        except Exception as e:
            print(f"    Decode error: {e}")
        return None

    def _build_article(self, url: str, fallback_title: str = '') -> Dict:
        result = self.text_extractor.extract(url, source='Google News')
        return {
            'url': result['url'],
            'title': result['title'] or fallback_title,
            'date': result['publish_date'],
            'text': result['text'],
            'summary': result['summary'],
            'source': 'Google News',
            'extracted_at': result['extracted_at'],
            'full_text_extracted': result['full_text_extracted'],
        }

    # ── Layer 1+2: RSS + decoder ──────────────────────────────────────────────

    def extract_from_rss(self, keywords: List[str], seen_urls: set) -> List[Dict]:
        """Fetch all RSS results for every keyword. Stops only on HTTP error."""
        articles = []
        print(f"\n  📡 Layer 1+2: RSS + URL decoder")

        for keyword in keywords:
            rss_url = (
                "https://news.google.com/rss/search?q="
                + quote_plus(keyword)
                + "&hl=en-IN&gl=IN&ceid=IN:en"
            )
            try:
                resp = requests.get(rss_url, headers=self.headers, timeout=15)
                if resp.status_code == 429:
                    print(f"    ⚠️  Rate limited (429) on '{keyword}' — stopping RSS")
                    break
                if resp.status_code != 200:
                    print(f"    RSS {resp.status_code} for '{keyword}' — skipping")
                    continue

                soup = BeautifulSoup(resp.content, 'xml')
                items = soup.find_all('item')
                print(f"  Keyword '{keyword}': {len(items)} RSS items")

                new_kw = 0
                for item in items:
                    title_tag = item.find('title')
                    link_tag  = item.find('link')
                    title = title_tag.text.strip() if title_tag else ''
                    google_url = link_tag.text.strip() if link_tag else ''

                    if not google_url or not self._is_crime_related(title):
                        continue
                    if self.text_extractor.is_video_url(google_url):
                        continue

                    real_url = self._decode_google_url(google_url)
                    if not real_url:
                        continue

                    real_url = self.text_extractor.clean_url(real_url)
                    if real_url in seen_urls:
                        continue

                    seen_urls.add(real_url)
                    print(f"    Extracting: {real_url[:80]}...")
                    articles.append(self._build_article(real_url, title))
                    new_kw += 1
                    time.sleep(1)

                print(f"    → {new_kw} new articles from '{keyword}'")
                time.sleep(1)

            except Exception as e:
                print(f"    RSS error for '{keyword}': {e}")

        print(f"  ✓ RSS+decoder: {len(articles)} articles")
        return articles

    # ── Layer 3: gnews library ────────────────────────────────────────────────

    def extract_from_gnews(self, keywords: List[str], seen_urls: set) -> List[Dict]:
        """Fetch all gnews results for every keyword. Stops only on error."""
        if not _GNEWS_AVAILABLE:
            print("  ⚠️  gnews not available, skipping Layer 3")
            return []

        articles = []
        print(f"\n  📰 Layer 3: gnews library")

        gn = GNews(language='en', country='IN', max_results=100)

        for keyword in keywords:
            try:
                results = gn.get_news(keyword)
                print(f"  Keyword '{keyword}': {len(results)} gnews results")

                new_kw = 0
                for item in results:
                    title = item.get('title', '')
                    google_url = item.get('url', '')

                    if not google_url or not self._is_crime_related(title):
                        continue
                    if self.text_extractor.is_video_url(google_url):
                        continue

                    real_url = self._decode_google_url(google_url)
                    if not real_url:
                        continue

                    real_url = self.text_extractor.clean_url(real_url)
                    if real_url in seen_urls:
                        continue

                    seen_urls.add(real_url)
                    print(f"    Extracting: {real_url[:80]}...")
                    articles.append(self._build_article(real_url, title))
                    new_kw += 1
                    time.sleep(1)

                print(f"    → {new_kw} new articles from '{keyword}'")
                time.sleep(1)

            except Exception as e:
                print(f"    gnews error for '{keyword}': {e}")

        print(f"  ✓ gnews: {len(articles)} articles")
        return articles

    # ── Combined ──────────────────────────────────────────────────────────────

    def extract(self, keywords: List[str], seen_urls: set = None) -> List[Dict]:
        """
        Both layers run independently over all keywords until exhausted or rate-limited.
        seen_urls deduplicates across both layers.
        """
        if seen_urls is None:
            seen_urls = set()
        all_articles = []

        print(f"\n{'='*60}")
        print(f"📰 Google News Extraction")
        print(f"{'='*60}")

        rss_articles = self.extract_from_rss(keywords, seen_urls)
        all_articles.extend(rss_articles)

        gnews_articles = self.extract_from_gnews(keywords, seen_urls)
        all_articles.extend(gnews_articles)

        text_ok = sum(1 for a in all_articles if a.get('full_text_extracted'))
        print(f"\n{'='*60}")
        print(f"✓ Google News Total : {len(all_articles)} articles")
        print(f"✓  Layer 1+2 (RSS)  : {len(rss_articles)}")
        print(f"✓  Layer 3 (gnews)  : {len(gnews_articles)}")
        print(f"✓ Text found        : {text_ok}/{len(all_articles)}")
        print(f"{'='*60}")
        return all_articles
