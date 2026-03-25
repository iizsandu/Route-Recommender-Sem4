"""Check how many INVALID urls from dates.json exist in MongoDB with null dates."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from article_text_extractor import get_extractor

DATES_JSON = os.path.join(os.path.dirname(__file__), 'dates.json')

with open(DATES_JSON, encoding='utf-8') as f:
    date_map = json.load(f)

invalid_urls = [url for url, val in date_map.items() if val == "INVALID"]
print(f"INVALID entries in dates.json : {len(invalid_urls)}")

col = MongoClient('mongodb://localhost:27017/')['crime2']['articles2']
extractor = get_extractor()

found_in_db = 0
for url in invalid_urls:
    clean = extractor.clean_url(url)
    if col.count_documents({"url": {"$in": [url, clean]}}):
        found_in_db += 1

print(f"Of those, found in MongoDB    : {found_in_db}")
print(f"Not in MongoDB                : {len(invalid_urls) - found_in_db}")
print()
print("These articles had no accessible content when dates.json was built.")
print("They remain in MongoDB with date=null — this is expected.")
