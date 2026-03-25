"""
Diagnose why Google News null-date articles didn't get matched in dates.json.
Compares MongoDB URLs vs dates.json keys for the same articles.
"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from article_text_extractor import get_extractor

DATES_JSON = os.path.join(os.path.dirname(__file__), 'dates.json')

with open(DATES_JSON, encoding='utf-8') as f:
    date_map = json.load(f)

col = MongoClient('mongodb://localhost:27017/')['crime2']['articles2']
extractor = get_extractor()

# Fetch null-date Google News articles
null_docs = list(col.find(
    {'source': 'Google News', '$or': [{'date': None}, {'date': {'$exists': False}}, {'date': ''}]},
    {'url': 1, '_id': 0}
).limit(20))

print(f"Checking {len(null_docs)} sample null-date Google News articles\n")
print(f"dates.json has {len(date_map)} entries\n")

matched = 0
for doc in null_docs:
    db_url = doc.get('url', '')
    cleaned = extractor.clean_url(db_url)
    in_json_raw    = db_url in date_map
    in_json_clean  = cleaned in date_map

    status = "MATCH(raw)" if in_json_raw else ("MATCH(clean)" if in_json_clean else "NO MATCH")
    if in_json_raw or in_json_clean:
        matched += 1
        val = date_map.get(db_url) or date_map.get(cleaned)
        print(f"  [{status}]  date={val}  {db_url[:70]}")
    else:
        print(f"  [NO MATCH]  db_url  : {db_url[:80]}")
        # Show closest key in date_map by prefix
        prefix = db_url[:50]
        close = [k for k in date_map if k.startswith(prefix[:40])]
        if close:
            print(f"             json_key: {close[0][:80]}")

print(f"\nMatched {matched}/{len(null_docs)} in dates.json")
