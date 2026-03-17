"""
Fix Empty Articles - Re-extract articles with empty text fields

This script:
1. Finds articles in articles2 collection with empty/missing text
2. Re-extracts them using the new centralized extractor (with URL cleaning)
3. Updates the database with the extracted content
"""

import sys
import os

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pymongo import MongoClient
from article_text_extractor import get_extractor
import time
from datetime import datetime

class EmptyArticleFixer:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["crime2"]
        self.collection = self.db["articles2"]
        self.extractor = get_extractor()
        
    def find_empty_articles(self):
        """Find articles with empty or missing text field"""
        query = {
            "$or": [
                {"text": {"$exists": False}},
                {"text": ""},
                {"text": None}
            ]
        }
        
        articles = list(self.collection.find(query))
        return articles
    
    def fix_article(self, article):
        """Re-extract article content using centralized extractor"""
        url = article.get('url')
        if not url:
            return False, "No URL found"
        
        try:
            # Extract using centralized extractor (with URL cleaning)
            result = self.extractor.extract(
                url=url,
                source=article.get('source', 'Google News'),
                keyword=article.get('keyword', '')
            )
            
            # Check if extraction was successful
            if not result.get('full_text_extracted'):
                return False, result.get('error', 'Extraction failed')
            
            # Update the article in database
            update_data = {
                "title": result.get('title', article.get('title', '')),
                "text": result.get('text', ''),
                "summary": result.get('summary', ''),
                "full_text_extracted": True,
                "text_length": result.get('text_length', 0),
                "re_extracted_at": datetime.now().isoformat()
            }
            
            self.collection.update_one(
                {"_id": article["_id"]},
                {"$set": update_data}
            )
            
            return True, f"Extracted {result.get('text_length', 0)} characters"
            
        except Exception as e:
            return False, str(e)
    
    def run(self, limit=None, delay=2):
        """
        Run the fixer
        
        Args:
            limit: Maximum number of articles to fix (None = all)
            delay: Delay between requests in seconds (default: 2)
        """
        print("=" * 70)
        print("Empty Article Fixer - Re-extraction Tool")
        print("=" * 70)
        print()
        
        # Find empty articles
        print("🔍 Searching for articles with empty text...")
        empty_articles = self.find_empty_articles()
        total_empty = len(empty_articles)
        
        print(f"✓ Found {total_empty} articles with empty text")
        print()
        
        if total_empty == 0:
            print("✓ No articles need fixing!")
            return
        
        # Apply limit if specified
        if limit:
            empty_articles = empty_articles[:limit]
            print(f"📋 Processing first {limit} articles (out of {total_empty})")
        else:
            print(f"📋 Processing all {total_empty} articles")
        
        print()
        print("=" * 70)
        print()
        
        # Process each article
        success_count = 0
        failed_count = 0
        
        for i, article in enumerate(empty_articles, 1):
            url = article.get('url', 'No URL')
            title = article.get('title', 'No Title')
            
            print(f"[{i}/{len(empty_articles)}] Processing...")
            print(f"  Title: {title[:60]}...")
            print(f"  URL: {url[:80]}...")
            
            # Clean URL display
            clean_url = self.extractor.clean_url(url)
            if clean_url != url:
                print(f"  Cleaned URL: {clean_url[:80]}...")
            
            # Try to fix
            success, message = self.fix_article(article)
            
            if success:
                print(f"  ✓ Success: {message}")
                success_count += 1
            else:
                print(f"  ✗ Failed: {message}")
                failed_count += 1
            
            print()
            
            # Delay between requests to avoid rate limiting
            if i < len(empty_articles):
                time.sleep(delay)
        
        # Summary
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print(f"Total processed: {len(empty_articles)}")
        print(f"✓ Successful: {success_count}")
        print(f"✗ Failed: {failed_count}")
        print(f"Success rate: {(success_count/len(empty_articles)*100):.1f}%")
        print()
        
        if failed_count > 0:
            print("Note: Some articles may have failed due to:")
            print("  - Paywalls or access restrictions")
            print("  - Invalid/broken URLs")
            print("  - Website blocking scraping")
            print("  - Network issues")
        
        print("=" * 70)


def main():
    """Main function with command line options"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fix articles with empty text by re-extracting them'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of articles to process (default: all)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check how many articles need fixing, do not process'
    )
    
    args = parser.parse_args()
    
    fixer = EmptyArticleFixer()
    
    if args.check_only:
        # Just check and report
        print("=" * 70)
        print("Checking for empty articles...")
        print("=" * 70)
        empty_articles = fixer.find_empty_articles()
        print(f"\n✓ Found {len(empty_articles)} articles with empty text")
        print("\nTo fix them, run:")
        print("  python fix_empty_articles.py")
        print("\nOr to fix only first 10:")
        print("  python fix_empty_articles.py --limit 10")
    else:
        # Run the fixer
        fixer.run(limit=args.limit, delay=args.delay)


if __name__ == "__main__":
    main()
