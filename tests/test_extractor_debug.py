"""
Extractor Debug Tool
====================
Run a single extractor in isolation, print results to terminal, and save to JSON.

Usage (from backend/ directory):
    python ../tests/test_extractor_debug.py --source google
    python ../tests/test_extractor_debug.py --source toi
    python ../tests/test_extractor_debug.py --source newsdata
    python ../tests/test_extractor_debug.py --source ndtv
    python ../tests/test_extractor_debug.py --source hindu
    python ../tests/test_extractor_debug.py --source indianexpress

Options:
    --source        Which extractor to test (required)
    --limit         Max articles to fetch (default: 5, use 0 for unlimited)
    --no-text       Skip full article text extraction (faster, just checks URL discovery)
    --rss-only      Only run RSS layer (skip web scrape)
    --scrape-only   Only run web scrape layer (skip RSS)
    --keywords      Comma-separated keywords override (google/newsdata only)

Output JSON saved to: tests/extractor_debug/<source>_debug.json
"""

import sys
import os
import json
import argparse
import time
from datetime import datetime
from typing import List, Dict

# ── Path setup so we can import from backend/ ────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, '..', 'backend')
sys.path.insert(0, BACKEND_DIR)

OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'extractor_debug')
os.makedirs(OUTPUT_DIR, exist_ok=True)

SOURCES = ['google', 'toi', 'newsdata', 'ndtv', 'hindu', 'indianexpress']


# ── Helpers ───────────────────────────────────────────────────────────────────

def truncate_text(text: str, max_chars: int = 300) -> str:
    if not text:
        return ''
    return text[:max_chars] + ('...' if len(text) > max_chars else '')


def print_article(idx: int, article: Dict):
    print(f"\n  [{idx}] {article.get('title', '(no title)')[:90]}")
    print(f"       URL   : {article.get('url', '')[:90]}")
    print(f"       Date  : {article.get('date') or article.get('published_date', '(none)')}")
    print(f"       Source: {article.get('source', '')}")
    text = article.get('text', '') or article.get('description', '')
    print(f"       Text  : {truncate_text(text, 200)}")
    print(f"       Full? : {article.get('full_text_extracted', False)}")


def print_summary(articles: List[Dict], source_name: str, elapsed: float):
    total = len(articles)
    with_text = sum(1 for a in articles if a.get('full_text_extracted'))
    with_date = sum(1 for a in articles if a.get('date') or a.get('published_date'))
    with_title = sum(1 for a in articles if a.get('title'))

    print(f"\n{'='*60}")
    print(f"  SUMMARY — {source_name}")
    print(f"{'='*60}")
    print(f"  Total articles   : {total}")
    print(f"  With full text   : {with_text}/{total}")
    print(f"  With date        : {with_date}/{total}")
    print(f"  With title       : {with_title}/{total}")
    print(f"  Time elapsed     : {elapsed:.1f}s")
    print(f"{'='*60}")


def save_json(articles: List[Dict], source: str, meta: Dict):
    out_path = os.path.join(OUTPUT_DIR, f"{source}_debug.json")
    payload = {
        "meta": meta,
        "articles": articles,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  💾 Saved {len(articles)} articles → {out_path}")


# ── Per-source runners ────────────────────────────────────────────────────────

def run_google(args):
    from google_news_extractor import GoogleNewsExtractor

    extractor = GoogleNewsExtractor()
    keywords = args.keywords.split(',') if args.keywords else [
        'Delhi crime', 'Delhi murder', 'Delhi police arrest', 'Delhi robbery'
    ]
    seen_urls = set()
    articles = []

    print(f"\n  Keywords: {keywords}")
    print(f"  Limit   : {args.limit if args.limit > 0 else 'unlimited'}")

    if not args.scrape_only:
        rss = extractor.extract_from_rss(keywords, seen_urls)
        articles.extend(rss)
        if args.limit > 0 and len(articles) >= args.limit:
            articles = articles[:args.limit]

    if not args.rss_only and (args.limit == 0 or len(articles) < args.limit):
        gnews = extractor.extract_from_gnews(keywords, seen_urls)
        articles.extend(gnews)
        if args.limit > 0:
            articles = articles[:args.limit]

    return articles


def run_toi(args):
    from toi_extractor import ArticleExtractor

    extractor = ArticleExtractor()
    seen_urls = set()
    articles = []

    if not args.scrape_only:
        rss = extractor.extract_from_rss(seen_urls=seen_urls)
        articles.extend(rss)
        if args.limit > 0 and len(articles) >= args.limit:
            return articles[:args.limit]

    if not args.rss_only:
        web = extractor.extract_from_web(seen_urls=seen_urls)
        articles.extend(web)

    if args.limit > 0:
        articles = articles[:args.limit]
    return articles


def run_newsdata(args):
    from newsdata_extractor import NewsDataExtractor

    extractor = NewsDataExtractor()
    keywords_override = args.keywords.split(',') if args.keywords else None
    if keywords_override:
        extractor.keywords = keywords_override

    # Use limit as max_credits if set, else default to 5 for debug
    max_credits = args.limit if args.limit > 0 else 5
    print(f"\n  ⚠️  NewsData uses API credits. Using max_credits={max_credits} for this debug run.")

    articles = extractor.fetch_articles(max_credits=max_credits)
    return articles


def run_ndtv(args):
    from ndtv_extractor import NDTVExtractor

    extractor = NDTVExtractor()
    seen_urls = set()
    articles = []

    if not args.scrape_only:
        rss = extractor.extract_from_rss(seen_urls)
        articles.extend(rss)
        if args.limit > 0 and len(articles) >= args.limit:
            return articles[:args.limit]

    if not args.rss_only:
        web = extractor.extract_from_web(seen_urls)
        articles.extend(web)

    if args.limit > 0:
        articles = articles[:args.limit]
    return articles


def run_hindu(args):
    from hindu_extractor import HinduExtractor

    extractor = HinduExtractor()
    seen_urls = set()
    articles = []

    if not args.scrape_only:
        rss = extractor.extract_from_rss(seen_urls)
        articles.extend(rss)
        if args.limit > 0 and len(articles) >= args.limit:
            return articles[:args.limit]

    if not args.rss_only:
        web = extractor.extract_from_web(seen_urls)
        articles.extend(web)

    if args.limit > 0:
        articles = articles[:args.limit]
    return articles


def run_indianexpress(args):
    from indian_express_extractor import IndianExpressExtractor

    extractor = IndianExpressExtractor()
    seen_urls = set()
    articles = []

    if not args.scrape_only:
        rss = extractor.extract_from_rss(seen_urls)
        articles.extend(rss)
        if args.limit > 0 and len(articles) >= args.limit:
            return articles[:args.limit]

    if not args.rss_only:
        web = extractor.extract_from_web(seen_urls)
        articles.extend(web)

    if args.limit > 0:
        articles = articles[:args.limit]
    return articles


# ── Main ──────────────────────────────────────────────────────────────────────

RUNNERS = {
    'google':        run_google,
    'toi':           run_toi,
    'newsdata':      run_newsdata,
    'ndtv':          run_ndtv,
    'hindu':         run_hindu,
    'indianexpress': run_indianexpress,
}

SOURCE_LABELS = {
    'google':        'Google News',
    'toi':           'Times of India',
    'newsdata':      'NewsData.io',
    'ndtv':          'NDTV',
    'hindu':         'The Hindu',
    'indianexpress': 'Indian Express',
}


def main():
    parser = argparse.ArgumentParser(
        description='Debug individual news extractors without MongoDB.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--source', required=True, choices=SOURCES,
        help=f'Extractor to test: {", ".join(SOURCES)}'
    )
    parser.add_argument(
        '--limit', type=int, default=5,
        help='Max articles to fetch (default: 5, use 0 for unlimited)'
    )
    parser.add_argument(
        '--rss-only', action='store_true',
        help='Only run RSS layer'
    )
    parser.add_argument(
        '--scrape-only', action='store_true',
        help='Only run web scrape layer'
    )
    parser.add_argument(
        '--keywords',
        help='Comma-separated keywords override (google/newsdata only)'
    )

    args = parser.parse_args()

    source_label = SOURCE_LABELS[args.source]
    print(f"\n{'='*60}")
    print(f"  🔍 Extractor Debug: {source_label}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.limit > 0:
        print(f"  Article limit: {args.limit}")
    else:
        print(f"  Article limit: UNLIMITED")
    if args.rss_only:
        print(f"  Mode: RSS only")
    elif args.scrape_only:
        print(f"  Mode: Web scrape only")
    print(f"{'='*60}")

    start = time.time()
    runner = RUNNERS[args.source]

    try:
        articles = runner(args)
    except Exception as e:
        print(f"\n  ❌ Fatal error running {source_label}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - start

    # Print each article
    print(f"\n{'─'*60}")
    print(f"  ARTICLES FOUND: {len(articles)}")
    print(f"{'─'*60}")
    for i, article in enumerate(articles, 1):
        print_article(i, article)

    print_summary(articles, source_label, elapsed)

    # Save JSON
    meta = {
        "source": args.source,
        "source_label": source_label,
        "run_at": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "limit": args.limit,
        "rss_only": args.rss_only,
        "scrape_only": args.scrape_only,
        "total_articles": len(articles),
        "with_full_text": sum(1 for a in articles if a.get('full_text_extracted')),
        "with_date": sum(1 for a in articles if a.get('date') or a.get('published_date')),
    }
    save_json(articles, args.source, meta)


if __name__ == '__main__':
    main()
