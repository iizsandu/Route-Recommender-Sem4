"""
Fix bad dates for bwpoliceworld.com articles.
All their dates were set to 2026-03-24 (the day build_date_map.py ran) — wrong.
This script:
  1. Nulls out the bad dates in MongoDB
  2. Re-fetches the correct date using the updated fallback extractor
  3. Updates MongoDB with the correct date

Run from repo root:
    python tests/fix_bwpoliceworld_dates.py
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from article_text_extractor import get_extractor
import requests
from bs4 import BeautifulSoup

MONGO_URL  = "mongodb://localhost:27017/"
BAD_DATE   = "2026-03-24T00:00:00"
DOMAIN     = "bwpoliceworld.com"
HEADERS    = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

col = MongoClient(MONGO_URL)['crime2']['articles2']
extractor = get_extractor()

# Find all bwpoliceworld articles with the bad date
bad_docs = list(col.find(
    {"url": {"$regex": DOMAIN}, "date": BAD_DATE},
    {"_id": 1, "url": 1}
))
print(f"Found {len(bad_docs)} bwpoliceworld articles with bad date {BAD_DATE}\n")

fixed = 0
failed = 0

for i, doc in enumerate(bad_docs, 1):
    url = doc['url']
    clean = extractor.clean_url(url)
    try:
        resp = requests.get(clean, headers=HEADERS, timeout=15)
        if not resp.ok or len(resp.text) < 500:
            print(f"  [{i:3d}] SKIP (no content)  {clean[:70]}")
            col.update_one({"_id": doc["_id"]}, {"$set": {"date": None}})
            failed += 1
            continue

        d = extractor._fallback_date_from_html(resp.text)
        if d:
            iso = d.isoformat()
            col.update_one({"_id": doc["_id"]}, {"$set": {"date": iso}})
            print(f"  [{i:3d}] FIXED  {iso}  {clean[:60]}")
            fixed += 1
        else:
            col.update_one({"_id": doc["_id"]}, {"$set": {"date": None}})
            print(f"  [{i:3d}] NULL   (no date found)  {clean[:60]}")
            failed += 1

        time.sleep(0.5)

    except Exception as e:
        col.update_one({"_id": doc["_id"]}, {"$set": {"date": None}})
        print(f"  [{i:3d}] ERROR  {str(e)[:60]}  {clean[:50]}")
        failed += 1

print(f"\n  Fixed  : {fixed}")
print(f"  Nulled : {failed}")
print(f"  Total  : {len(bad_docs)}")
