"""
Simple script to check how many URLs from extraction_progress.json and
google_news_progress.json are not yet stored in MongoDB (crime2.articles2)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient

MONGO_URL = "mongodb://localhost:27017/"
DB_NAME = "crime2"
COLLECTION_NAME = "articles2"

PROGRESS_FILES = [
    os.path.join(os.path.dirname(__file__), '..', 'backend', 'extraction_progress.json'),
    os.path.join(os.path.dirname(__file__), '..', 'backend', 'google_news_progress.json'),
]


def load_urls_from_file(filepath: str) -> set:
    """Extract all URLs from a progress JSON file."""
    urls = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # seen_urls is a flat list (extraction_progress.json)
        for url in data.get('seen_urls', []):
            if url:
                urls.add(url.strip())

        # articles array may also contain urls (google_news_progress.json)
        for article in data.get('articles', []):
            url = article.get('url', '').strip()
            if url:
                urls.add(url)

    except FileNotFoundError:
        print(f"File not found: {filepath}")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")

    return urls


def main():
    # Load URLs from both files
    all_urls = set()
    for filepath in PROGRESS_FILES:
        urls = load_urls_from_file(filepath)
        all_urls.update(urls)

    print(f"Total unique URLs across both files: {len(all_urls)}")

    # Connect to MongoDB
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        client.server_info()
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # Count missing URLs
    missing_count = 0
    for url in all_urls:
        if not collection.find_one({"url": url}, {"_id": 1}):
            missing_count += 1

    print(f"URLs yet to be stored in MongoDB: {missing_count}")


if __name__ == "__main__":
    main()
