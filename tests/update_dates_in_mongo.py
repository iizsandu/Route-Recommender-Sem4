"""
Task 1: Populate `date` field in MongoDB for the 3250 articles that had no date.

Rules:
- Source: tests/dates.json  { cleaned_url: "ISO-8601" | null | "INVALID" }
- Only update documents where `date` is currently null/missing
- Skip entries where dates.json value is "INVALID" (no article content)
- Skip entries where dates.json value is null (manual fill pending)
- Match MongoDB URLs via clean_url() to handle trailing tracking params

Run from repo root:
    python tests/update_dates_in_mongo.py
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from article_text_extractor import get_extractor

DATES_JSON = os.path.join(os.path.dirname(__file__), 'dates.json')
MONGO_URL  = "mongodb://localhost:27017/"
DB_NAME    = "crime2"
COLLECTION = "articles2"


def main():
    with open(DATES_JSON, encoding='utf-8') as f:
        date_map: dict = json.load(f)

    # Filter: only entries with an actual date string
    actionable = {url: val for url, val in date_map.items() if val and val != "INVALID"}
    print(f"  dates.json total entries : {len(date_map)}")
    print(f"  Entries with a date      : {len(actionable)}")
    print(f"  INVALID (skipped)        : {sum(1 for v in date_map.values() if v == 'INVALID')}")
    print(f"  null (manual, skipped)   : {sum(1 for v in date_map.values() if v is None)}")

    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    col = client[DB_NAME][COLLECTION]
    extractor = get_extractor()

    # Fetch all null-date docs and match via clean_url
    null_docs = list(col.find(
        {'$or': [{'date': None}, {'date': {'$exists': False}}, {'date': ''}]},
        {'_id': 1, 'url': 1}
    ))
    print(f"\n  Null-date docs in DB     : {len(null_docs)}")

    updated = 0
    no_match = 0

    for doc in null_docs:
        raw_url = doc.get('url', '')
        clean = extractor.clean_url(raw_url)

        # Try cleaned URL first, then raw
        date_val = actionable.get(clean) or actionable.get(raw_url)
        if not date_val:
            no_match += 1
            continue

        col.update_one({'_id': doc['_id']}, {'$set': {'date': date_val}})
        updated += 1

    print(f"\n  Results:")
    print(f"  Updated                  : {updated}")
    print(f"  No match in dates.json   : {no_match}")
    print(f"\n  Done.")
    client.close()


if __name__ == "__main__":
    main()
