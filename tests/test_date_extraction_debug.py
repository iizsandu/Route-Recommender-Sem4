"""
Date extraction debugger.
Run: python tests/test_date_extraction_debug.py <url> [<url2> ...]
Or edit URLS list below and run without arguments.

Shows:
  - Extracted date
  - Which strategy found it (S0=newspaper3k, S1-S6=HTML fallbacks)
  - Article title and text length
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from newspaper import Article
import requests as _requests
from article_text_extractor import ArticleTextExtractor

# ── Edit this list to test multiple URLs at once ───────────────────────────────
URLS = [
    "https://www.bwpoliceworld.com/article/delhi-crime-branch-busted-a-counterfeit-food-items-from-uttamnagar-585476",
]


def check_url(url: str, extractor: ArticleTextExtractor):
    print(f"\n{'─'*70}")
    print(f"URL: {url}")
    print(f"{'─'*70}")

    clean = extractor.clean_url(url)

    # Download HTML
    article = Article(clean)
    html = None
    newspaper_date = None

    try:
        article.download()
        if article.html and len(article.html) > 500:
            html = article.html
        else:
            raise Exception("newspaper HTML empty")
    except Exception:
        try:
            resp = _requests.get(clean, headers=extractor.headers, timeout=15)
            resp.raise_for_status()
            html = resp.text
            article.set_html(html)
        except Exception as e:
            print(f"  ✗ Could not fetch HTML: {e}")
            return

    try:
        article.parse()
        article.nlp()
        newspaper_date = article.publish_date
        title = article.title
        text_len = len(article.text) if article.text else 0
    except Exception as e:
        print(f"  ✗ newspaper parse failed: {e}")
        title = ""
        text_len = 0

    print(f"  Title      : {title or '(none)'}")
    print(f"  Text length: {text_len} chars")
    print(f"  newspaper3k date: {newspaper_date}")

    # Run date extraction with strategy reporting
    report = []
    date = extractor._extract_publish_date(clean, newspaper_date, html, _report=report)

    if date:
        strategy = report[0] if report else "unknown"
        print(f"\n  ✓ Date found : {date.strftime('%Y-%m-%d %H:%M') if hasattr(date, 'strftime') else date}")
        print(f"  ✓ Strategy   : {strategy}")
    else:
        print(f"\n  ✗ No date extracted — all strategies failed")

    # Show all strategies that were attempted (only the winner is in report)
    print(f"\n  Strategy log: {report if report else '(none succeeded)'}")


def main():
    urls = sys.argv[1:] if len(sys.argv) > 1 else URLS
    if not urls:
        print("Usage: python tests/test_date_extraction_debug.py <url> [<url2> ...]")
        sys.exit(1)

    extractor = ArticleTextExtractor()
    for url in urls:
        check_url(url.strip(), extractor)

    print(f"\n{'─'*70}")
    print(f"Done. {len(urls)} URL(s) checked.")


if __name__ == "__main__":
    main()
