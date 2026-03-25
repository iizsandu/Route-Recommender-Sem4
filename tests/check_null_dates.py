"""Quick diagnostic: breakdown of null-date articles in MongoDB."""
from pymongo import MongoClient
from collections import Counter

col = MongoClient('mongodb://localhost:27017/')['crime2']['articles2']

total     = col.count_documents({})
null_date = col.count_documents({'$or': [{'date': None}, {'date': {'$exists': False}}, {'date': ''}]})
has_date  = total - null_date

print(f"Total articles : {total}")
print(f"Has date       : {has_date}")
print(f"Null date      : {null_date}")

# Source breakdown
sources = [d.get('source', 'Unknown') for d in col.find(
    {'$or': [{'date': None}, {'date': {'$exists': False}}, {'date': ''}]},
    {'source': 1, '_id': 0}
)]
print("\nNull-date by source:")
for src, cnt in Counter(sources).most_common():
    print(f"  {cnt:>5}  {src}")

# Sample 8 URLs
print("\nSample null-date URLs:")
for doc in col.find(
    {'$or': [{'date': None}, {'date': {'$exists': False}}, {'date': ''}]},
    {'url': 1, 'source': 1, 'extracted_at': 1, '_id': 0}
).limit(8):
    print(f"  [{doc.get('source','?')[:20]}]  {doc.get('url','')[:80]}")
