"""
Refresh publish dates for ALL articles in MongoDB.

Logic per article:
  1. Fetch the URL, attempt text extraction.
  2. If article text NOT extractable  → set date = "Invalid"
  3. If article text IS extractable:
       a. Date found  → set date = ISO string (YYYY-MM-DD)
       b. Date not found → set date = None (null)

Replaces whatever is currently in the `date` field — no skipping.

Run:
    backend\\venv\\Scripts\\python.exe tests/refresh_dates_in_mongo.py

Optional flags:
    --limit 100        process only first N articles (for testing)
    --dry-run          print what would change, no DB writes
"""
import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from newspaper import Article
import requests as _requests
from article_text_extractor import ArticleTextExtractor

MONGO_URL   = "mongodb://localhost:27017/"
DB_NAME     = "crime2"
COLLECTION  = "articles2"

# ── helpers ───────────────────────────────────────────────────────────────────

def fetch_html(url: str, headers: dict) -> tuple[str | None, bool]:
    """
    Returns (html, text_extractable).
    text_extractable = True if we got meaningful HTML (>=500 chars).
    """
    # Try newspaper first
    try:
        art = Article(url)
        art.download()
        if art.html and len(art.html) > 500:
            return art.html, True
    except Exception:
        pass

    # Fallback: requests
    try:
        resp = _requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        if len(resp.text) > 500:
            return resp.text, True
    except Exception:
        pass

    return None, False


def extract_text_check(url: str, extractor: ArticleTextExtractor) -> tuple[bool, str | None]:
    """
    Returns (text_present, date_iso_or_none).
    text_present = False means the page is inaccessible / no content.
    """
    html, accessible = fetch_html(url, extractor.headers)
    if not accessible:
        return False, None

    # Try to parse text via newspaper
    try:
        art = Article(url)
        art.set_html(html)
        art.parse()
        text_ok = bool(art.text and len(art.text.strip()) >= 100)
        newspaper_date = art.publish_date if text_ok else None
    except Exception:
        text_ok = False
        newspaper_date = None

    if not text_ok:
        return False, None

    # Extract date
    report = []
    date_obj = extractor._extract_publish_date(url, newspaper_date, html, _report=report)
    strategy = report[0] if report else None

    if date_obj:
        try:
            date_iso = date_obj.strftime('%Y-%m-%d')
        except Exception:
            date_iso = str(date_obj)[:10]
        return True, date_iso

    return True, None   # text present but no date found


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0, help='Process only first N articles (0 = all)')
    parser.add_argument('--dry-run', action='store_true', help='Print changes without writing to DB')
    args = parser.parse_args()

    client = MongoClient(MONGO_URL)
    col    = client[DB_NAME][COLLECTION]
    extractor = ArticleTextExtractor()

    query  = {}
    cursor = col.find(query, {'_id': 1, 'url': 1, 'date': 1})
    docs   = list(cursor)
    if args.limit:
        docs = docs[:args.limit]

    total   = len(docs)
    updated = 0
    invalid = 0
    null_date = 0
    dated   = 0
    errors  = 0

    print(f"Processing {total} articles {'(DRY RUN)' if args.dry_run else ''}...\n")

    for i, doc in enumerate(docs, 1):
        url = doc.get('url', '')
        old_date = doc.get('date')
        _id = doc['_id']

        if not url:
            continue

        clean = extractor.clean_url(url)

        try:
            text_present, date_iso = extract_text_check(clean, extractor)
        except Exception as e:
            print(f"  [{i}/{total}] ERROR {clean[:60]} — {e}")
            errors += 1
            continue

        if not text_present:
            new_date = "Invalid"
            invalid += 1
            tag = "INVALID"
        elif date_iso:
            new_date = date_iso
            dated += 1
            tag = f"DATE    {date_iso}"
        else:
            new_date = None
            null_date += 1
            tag = "NULL"

        changed = (old_date != new_date)
        marker  = "→" if changed else "="

        print(f"  [{i}/{total}] {marker} {tag:<22} {clean[:55]}")

        if not args.dry_run and changed:
            col.update_one({'_id': _id}, {'$set': {'date': new_date}})
            updated += 1

        # Progress checkpoint every 100
        if i % 100 == 0:
            print(f"\n  --- checkpoint {i}/{total} | dated={dated} invalid={invalid} null={null_date} updated={updated} ---\n")

    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"  Total processed : {total}")
    print(f"  Dated           : {dated}")
    print(f"  Null (no date)  : {null_date}")
    print(f"  Invalid (no text): {invalid}")
    print(f"  DB rows updated : {updated}  {'(dry run — no writes)' if args.dry_run else ''}")
    print(f"  Errors          : {errors}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
