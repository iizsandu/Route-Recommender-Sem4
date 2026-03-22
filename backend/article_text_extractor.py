"""
Centralized Article Text Extractor
Single source of truth for all article text extraction
Used as an API by all other extractors before database storage
"""
from newspaper import Article
from datetime import datetime
from typing import Dict, Optional
import requests as _requests

class ArticleTextExtractor:
    """
    Centralized article text extraction service
    All article URLs must pass through this extractor before database storage
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
    
    def _try_newspaper_download(self, article: Article) -> bool:
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
                'publish_date': article.publish_date,
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
