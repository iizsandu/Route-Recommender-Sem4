"""
Centralized Article Text Extractor
Single source of truth for all article text extraction
Used as an API by all other extractors before database storage
"""
from newspaper import Article
from datetime import datetime, timezone
from typing import Dict, Optional
import re
import json
import requests as _requests
from bs4 import BeautifulSoup

try:
    from dateutil import parser as _dateutil_parser
    _DATEUTIL_AVAILABLE = True
except ImportError:
    _DATEUTIL_AVAILABLE = False

# ── Date patterns for fallback extraction ─────────────────────────────────────
_DATE_PATTERNS = [
    re.compile(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)?'),
    re.compile(r'\b\d{4}-\d{2}-\d{2}\b'),
    re.compile(
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{1,2},?\s+\d{4}(?:[,\s]+\d{1,2}:\d{2}(?:\s*[AP]M)?(?:\s*IST)?)?',
        re.IGNORECASE
    ),
    re.compile(
        r'\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{4}\b',
        re.IGNORECASE
    ),
    re.compile(r'\b\d{1,2}[/\.]\d{1,2}[/\.]\d{4}\b'),
]

class ArticleTextExtractor:
    """
    Centralized article text extraction service
    All article URLs must pass through this extractor before database storage
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
        }
    
    def clean_url(self, url: str) -> str:
        """Clean URL by removing tracking parameters."""
        if not url:
            return url

        tracking_params = [
            '&ved=', '&usg=', '&sa=', '&source=', '&cd=', '&cad=',
            '&utm_source=', '&utm_medium=', '&utm_campaign=',
            '&fbclid=', '&gclid='
        ]
        for param in tracking_params:
            if param in url:
                url = url.split(param)[0]
        return url

    def is_video_url(self, url: str) -> bool:
        """Return True for YouTube/video URLs that have no article text to extract."""
        video_patterns = ['youtube.com', 'youtu.be', 'youtube.com/watch']
        return any(p in url.lower() for p in video_patterns)
    
    def _parse_date(self, raw: str) -> Optional[datetime]:
        """Parse a raw date string into a datetime using dateutil."""
        if not raw or not _DATEUTIL_AVAILABLE:
            return None
        try:
            cleaned = re.sub(r'\s*IST\s*$', '', raw.strip(), flags=re.IGNORECASE)
            return _dateutil_parser.parse(cleaned, fuzzy=True)
        except Exception:
            return None

    def _first_date_in(self, text: str) -> Optional[datetime]:
        """Return the first parseable date found in text using known patterns."""
        for pat in _DATE_PATTERNS:
            m = pat.search(text)
            if m:
                d = self._parse_date(m.group())
                if d:
                    return d
        return None

    def _is_plausible_date(self, d: datetime) -> bool:
        """
        Reject dates that are clearly wrong:
        - In the future (today or later) — catches 'today's date' false positives
        - More than 15 years in the past — no news article is that old in this DB
        """
        now = datetime.now()
        # Strip timezone for comparison
        dt = d.replace(tzinfo=None) if d.tzinfo else d
        if dt.date() >= now.date():
            return False
        if dt.year < (now.year - 15):
            return False
        return True

    def _fallback_date_from_html(self, html: str, _report: list = None) -> Optional[datetime]:
        """
        8-strategy fallback date extraction from raw HTML.
        Strategies (in order):
          1. itemprop="datePublished"  (schema.org)
          2. itemprop="dateModified"   (schema.org fallback)
          3. <meta> tags               (og/DC/pubdate properties)
          4. JSON-LD <script>          (structured data)
          5. Classed elements          (byline/timestamp/date class names)
          6. Full-page keyword scan    (near published/updated/posted)
          7. Full-page early scan      (any date in first 5000 chars)
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            return None

        # 1. itemprop="datePublished"
        tag = soup.find(itemprop='datePublished')
        if tag:
            d = self._parse_date(tag.get('content') or tag.get_text(strip=True))
            if d:
                if _report is not None: _report.append('S1: itemprop=datePublished')
                return d

        # 2. itemprop="dateModified"
        tag = soup.find(itemprop='dateModified')
        if tag:
            d = self._parse_date(tag.get('content') or tag.get_text(strip=True))
            if d:
                if _report is not None: _report.append('S2: itemprop=dateModified')
                return d

        # 3. <meta> tags
        for prop in ['article:published_time', 'og:article:published_time',
                     'DC.date', 'pubdate', 'date', 'article:modified_time']:
            tag = (soup.find('meta', attrs={'property': prop}) or
                   soup.find('meta', attrs={'name': prop}))
            if tag and tag.get('content'):
                d = self._parse_date(tag['content'])
                if d:
                    if _report is not None: _report.append(f'S3: <meta> {prop}')
                    return d

        # 4. JSON-LD structured data
        for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
            try:
                data = json.loads(script.string or '')
                items = data if isinstance(data, list) else [data]
                for item in items:
                    for key in ('datePublished', 'dateCreated', 'dateModified'):
                        val = item.get(key)
                        if val:
                            d = self._parse_date(val)
                            if d:
                                if _report is not None: _report.append(f'S4: JSON-LD {key}')
                                return d
            except Exception:
                pass

        # 5. Elements with date-related class names
        for el in soup.find_all(True, attrs={'class': re.compile(
                r'byline|dateline|timestamp|publish|posted|updated|article.?date|pub.?date', re.I)}):
            d = self._first_date_in(el.get_text(' ', strip=True))
            if d and self._is_plausible_date(d):
                if _report is not None: _report.append(f'S5: class={el.get("class")}')
                return d

        # 5b. Calendar/clock icon sibling (fa-calendar, fa-clock, etc.)
        for icon in soup.find_all('i', attrs={'class': re.compile(r'fa-(calendar|clock|time)', re.I)}):
            parent = icon.parent
            if parent:
                text = parent.get_text(' ', strip=True)
                d = self._first_date_in(text)
                if d and self._is_plausible_date(d):
                    if _report is not None: _report.append('S5b: calendar icon parent')
                    return d
                sib = parent.find_next_sibling()
                if sib:
                    d = self._first_date_in(sib.get_text(' ', strip=True))
                    if d and self._is_plausible_date(d):
                        if _report is not None: _report.append('S5b: calendar icon sibling')
                        return d

        # 6. First date after the article <h1> title (post-title scan, 500 char window)
        title_tag = (
            soup.find('h1') or
            soup.find(attrs={'class': re.compile(r'title|headline|article-title', re.I)})
        )
        if title_tag:
            post_title_text = []
            for el in title_tag.find_all_next(string=True):
                chunk = el.strip()
                if chunk:
                    post_title_text.append(chunk)
                if sum(len(c) for c in post_title_text) > 500:
                    break
            window = ' '.join(post_title_text)
            d = self._first_date_in(window)
            if d and self._is_plausible_date(d):
                if _report is not None: _report.append('S6: post-title scan')
                return d

        return None

    def _extract_publish_date(self, url: str, newspaper_date: Optional[datetime], html: Optional[str], _report: list = None) -> Optional[datetime]:
        """
        Get publish date: newspaper3k first, then fallback strategies.
        _report: if a list is passed, the winning strategy name is appended to it.
        """
        if newspaper_date:
            if _report is not None: _report.append('S0: newspaper3k')
            return newspaper_date

        if html:
            return self._fallback_date_from_html(html, _report)

        try:
            resp = _requests.get(url, headers=self.headers, timeout=15)
            if resp.ok and len(resp.text) > 500:
                return self._fallback_date_from_html(resp.text, _report)
        except Exception:
            pass

        return None

    def _try_newspaper_download(self, article) -> bool:
        """Attempt newspaper's built-in download. Returns True if HTML was fetched."""
        try:
            article.download()
            # newspaper swallows errors — check if HTML actually landed
            return bool(article.html and len(article.html) > 500)
        except Exception:
            return False

    def _try_requests_download(self, url: str, article: Article) -> bool:
        """Fallback: fetch HTML with requests and inject into newspaper."""
        try:
            resp = _requests.get(url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            article.set_html(resp.text)
            return True
        except Exception:
            return False

    def extract(self, url: str, source: Optional[str] = None, keyword: Optional[str] = None) -> Dict:
        """
        Extract full article text from URL
        This is the ONLY method that should be used for article extraction
        
        Args:
            url: Article URL (will be cleaned automatically)
            source: Source name (e.g., "Google News", "Times of India")
            keyword: Search keyword used to find article (optional)
            
        Returns:
            Dictionary with standardized article data:
            {
                'url': str,              # Cleaned URL
                'title': str,            # Article title
                'authors': list,         # List of authors
                'publish_date': datetime,# Publish date
                'text': str,             # Full article text
                'summary': str,          # AI-generated summary
                'keywords': list,        # Extracted keywords
                'top_image': str,        # Main image URL
                'source': str,           # Source name
                'keyword': str,          # Search keyword (if provided)
                'extracted_at': str,     # ISO timestamp
                'full_text_extracted': bool,  # Success status
                'text_length': int,      # Character count
                'error': str             # Error message (if failed)
            }
        """
        # Clean URL first
        clean_url = self.clean_url(url)

        # Reject video URLs — no article text to extract
        if self.is_video_url(clean_url):
            return {
                'url': clean_url, 'title': '', 'authors': [], 'publish_date': None,
                'text': '', 'summary': '', 'keywords': [], 'top_image': '',
                'source': source or 'Unknown', 'keyword': keyword or '',
                'extracted_at': datetime.now().isoformat(),
                'full_text_extracted': False, 'text_length': 0,
                'error': 'Skipped: YouTube/video URL'
            }
        
        try:
            article = Article(clean_url)

            # Stage 1: newspaper's own downloader
            downloaded = self._try_newspaper_download(article)

            # Stage 2: fallback to requests if newspaper failed or returned empty HTML
            if not downloaded:
                print(f"  ⚠️  newspaper download failed, trying requests fallback...")
                downloaded = self._try_requests_download(clean_url, article)

            if not downloaded:
                raise Exception("Both newspaper and requests download failed")

            article.parse()
            article.nlp()

            # Checkpoint: reject articles with no meaningful text
            if not article.text or len(article.text.strip()) < 100:
                raise Exception(f"Extracted text too short ({len(article.text.strip()) if article.text else 0} chars) — page may be paywalled or JS-rendered")

            return {
                'url': clean_url,
                'title': article.title or '',
                'authors': article.authors or [],
                'publish_date': self._extract_publish_date(clean_url, article.publish_date, article.html),
                'text': article.text or '',
                'summary': article.summary or '',
                'keywords': article.keywords or [],
                'top_image': article.top_image or '',
                'source': source or 'Unknown',
                'keyword': keyword or '',
                'extracted_at': datetime.now().isoformat(),
                'full_text_extracted': True,
                'text_length': len(article.text),
                'error': None
            }
            
        except Exception as e:
            # Return failed result with error
            return {
                'url': clean_url,
                'title': '',
                'authors': [],
                'publish_date': None,
                'text': '',
                'summary': '',
                'keywords': [],
                'top_image': '',
                'source': source or 'Unknown',
                'keyword': keyword or '',
                'extracted_at': datetime.now().isoformat(),
                'full_text_extracted': False,
                'text_length': 0,
                'error': str(e)
            }
    
    def extract_batch(self, urls: list, source: Optional[str] = None) -> list:
        """
        Extract multiple articles in batch
        
        Args:
            urls: List of article URLs
            source: Source name for all articles
            
        Returns:
            List of extraction results
        """
        results = []
        
        for url in urls:
            result = self.extract(url, source=source)
            results.append(result)
        
        return results
    
    def validate_extraction(self, result: Dict) -> bool:
        """
        Validate if extraction was successful and has minimum content
        
        Args:
            result: Extraction result dictionary
            
        Returns:
            True if extraction is valid, False otherwise
        """
        if not result.get('full_text_extracted'):
            return False
        
        # Check minimum text length (at least 100 characters)
        if result.get('text_length', 0) < 100:
            return False
        
        # Check if title exists
        if not result.get('title'):
            return False
        
        return True


# Global singleton instance
_extractor_instance = None

def get_extractor() -> ArticleTextExtractor:
    """
    Get global article text extractor instance (singleton pattern)
    
    Returns:
        ArticleTextExtractor instance
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = ArticleTextExtractor()
    return _extractor_instance
