"""
Fix Empty Articles
Finds articles with no text (excluding YouTube and unresolvable news.google.com redirects).
For Google News CBMi URLs: decodes them first using googlenewsdecoder, then extracts.
For all others: extracts directly.
Updates the document with text + cleaned URL.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from article_text_extractor import get_extractor
import time
from datetime import datetime

try:
    from googlenewsdecoder import gnewsdecoder
    _DECODER_AVAILABLE = True
except ImportError:
    _DECODER_AVAILABLE = False
    print("⚠️  googlenewsdecoder not installed — Google News CBMi URLs will be skipped")


def _decode_google_url(url: str) -> str:
    """Resolve CBMi redirect to real article URL. Returns None if fails."""
    if not _DECODER_AVAILABLE or 'news.google.com' not in url:
        return url
    try:
        result = gnewsdecoder(url, interval=1)
        if result.get('status'):
            real = result['decoded_url']
            if 'news.google.com' not in real:
                return real
    except Exception:
        pass
    return None


def _is_skippable(url: str) -> bool:
    """URLs we can never extract text from."""
    skip_patterns = [
        'youtube.com',
        'youtu.be',
    ]
    return any(p in url for p in skip_patterns)


class EmptyArticleFixer:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["crime2"]
        self.collection = self.db["articles2"]
        self.extractor = get_extractor()

    def find_empty_articles(self):
        query = {
            "$or": [
                {"text": {"$exists": False}},
                {"text": ""},
                {"text": None},
                {"full_text_extracted": False}
            ]
        }
        return list(self.collection.find(query))

    def fix_article(self, article) -> tuple:
        url = article.get('url', '')
        if not url:
            return False, "No URL"

        if _is_skippable(url):
            return False, "Skipped (YouTube/video URL)"

        # For Google News CBMi URLs — decode first
        working_url = url
        if 'news.google.com' in url:
            decoded = _decode_google_url(url)
            if not decoded:
                return False, "Google News redirect — could not decode"
            working_url = decoded

        # Clean tracking params
        working_url = self.extractor.clean_url(working_url)

        try:
            result = self.extractor.extract(url=working_url, source=article.get('source', ''))

            if not result.get('full_text_extracted'):
                return False, result.get('error', 'Extraction failed')[:80]

            self.collection.update_one(
                {"_id": article["_id"]},
                {"$set": {
                    "url": working_url,          # store the resolved/cleaned URL
                    "title": result.get('title') or article.get('title', ''),
                    "text": result.get('text', ''),
                    "summary": result.get('summary', ''),
                    "full_text_extracted": True,
                    "text_length": result.get('text_length', 0),
                    "re_extracted_at": datetime.now().isoformat()
                }}
            )
            return True, f"{result.get('text_length', 0)} chars"

        except Exception as e:
            return False, str(e)[:80]

    def run(self, limit=None, delay=2):
        print("=" * 70)
        print("Empty Article Fixer")
        print("=" * 70)

        total_in_db = self.collection.count_documents({})
        all_empty = self.find_empty_articles()

        # Categorise
        skippable  = [a for a in all_empty if _is_skippable(a.get('url', ''))]
        gn_redirect = [a for a in all_empty
                       if 'news.google.com' in a.get('url', '')
                       and not _is_skippable(a.get('url', ''))]
        fixable    = [a for a in all_empty
                      if not _is_skippable(a.get('url', ''))
                      and 'news.google.com' not in a.get('url', '')]

        print(f"\n📊 Total in DB           : {total_in_db}")
        print(f"❌ Empty text total      : {len(all_empty)}")
        print(f"   ├─ YouTube/video      : {len(skippable)}  (skipped)")
        print(f"   ├─ Google News CBMi   : {len(gn_redirect)}  (decode + extract)")
        print(f"   └─ Other fixable      : {len(fixable)}  (extract directly)")

        # Process: Google News redirects + other fixable
        to_process = gn_redirect + fixable
        if limit:
            to_process = to_process[:limit]

        if not to_process:
            print("\n✓ Nothing to fix!")
            return

        print(f"\n📋 Processing {len(to_process)} articles (delay={delay}s)")
        print("=" * 70)

        success = 0
        failed  = 0
        skipped = 0

        for i, article in enumerate(to_process, 1):
            url = article.get('url', '')
            title = article.get('title', 'No title')
            is_gn = 'news.google.com' in url

            print(f"\n[{i}/{len(to_process)}] {'[GN decode] ' if is_gn else ''}{title[:55]}...")
            print(f"  URL: {url[:80]}")

            ok, msg = self.fix_article(article)

            if ok:
                print(f"  ✅ {msg}")
                success += 1
            elif "Skipped" in msg:
                print(f"  ⏭️  {msg}")
                skipped += 1
            else:
                print(f"  ❌ {msg}")
                failed += 1

            if i < len(to_process):
                time.sleep(delay)

        print(f"\n{'=' * 70}")
        print(f"✅ Success : {success}")
        print(f"❌ Failed  : {failed}")
        print(f"⏭️  Skipped : {skipped}")
        print(f"Rate      : {success/(success+failed)*100:.1f}%" if (success+failed) else "")
        print("=" * 70)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fix articles with empty text')
    parser.add_argument('--limit', type=int, default=None, help='Max articles to process')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests (s)')
    parser.add_argument('--check-only', action='store_true', help='Only show counts, do not fix')
    args = parser.parse_args()

    fixer = EmptyArticleFixer()

    if args.check_only:
        print("=" * 70)
        print("Checking for empty articles...")
        print("=" * 70)
        total_in_db = fixer.collection.count_documents({})
        all_empty = fixer.find_empty_articles()
        skippable   = [a for a in all_empty if _is_skippable(a.get('url', ''))]
        gn_redirect = [a for a in all_empty
                       if 'news.google.com' in a.get('url', '')
                       and not _is_skippable(a.get('url', ''))]
        fixable     = [a for a in all_empty
                       if not _is_skippable(a.get('url', ''))
                       and 'news.google.com' not in a.get('url', '')
                       ]
        print(f"\n📊 Total articles in DB  : {total_in_db}")
        print(f"❌ Articles with no text : {len(all_empty)}")
        print(f"   ├─ YouTube/video      : {len(skippable)}  (unrecoverable)")
        print(f"   ├─ Google News CBMi   : {len(gn_redirect)}  (decode + extract)")
        print(f"   └─ Other fixable      : {len(fixable)}")
        print(f"\nTo fix them, run:")
        print(f"  python fix_empty_articles.py")
        print(f"Or first 20 only:")
        print(f"  python fix_empty_articles.py --limit 20")
    else:
        fixer.run(limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
