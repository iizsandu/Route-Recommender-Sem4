"""
Simple Article Text Extractor - Test Version
Extracts full text from article URLs using newspaper3k
Same logic as backend/article_extractor.py
"""
from newspaper import Article
from datetime import datetime

class SimpleArticleExtractor:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def clean_url(self, url: str) -> str:
        """
        Clean URL by removing tracking parameters
        Removes everything after &ved, &usg, &sa, etc.
        
        Args:
            url: Raw URL with tracking parameters
            
        Returns:
            Cleaned URL without tracking parameters
        """
        if not url:
            return url
        
        # Remove common tracking parameters
        tracking_params = ['&ved=', '&usg=', '&sa=', '&source=', '&cd=', '&cad=']
        
        for param in tracking_params:
            if param in url:
                url = url.split(param)[0]
        
        return url
    
    def extract_article_text(self, url: str) -> dict:
        """
        Extract full article text from URL
        
        Args:
            url: Article URL
            
        Returns:
            Dictionary with article content
        """
        # Clean URL first
        clean_url = self.clean_url(url)
        
        print(f"\n{'='*70}")
        print(f"Original URL: {url}")
        if clean_url != url:
            print(f"Cleaned URL:  {clean_url}")
        print(f"{'='*70}")
        
        try:
            # Create article object with cleaned URL
            article = Article(clean_url)
            
            # Download article
            print("📥 Downloading article...")
            article.download()
            
            # Parse article
            print("📄 Parsing article...")
            article.parse()
            
            # Perform NLP (summary, keywords)
            print("🧠 Performing NLP...")
            article.nlp()
            
            # Extract data
            result = {
                'url': clean_url,  # Store cleaned URL
                'title': article.title,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'text': article.text,
                'summary': article.summary,
                'keywords': article.keywords,
                'top_image': article.top_image,
                'extracted_at': datetime.now().isoformat(),
                'success': True
            }
            
            # Print results
            print(f"\n✓ Extraction Successful!")
            print(f"{'='*70}")
            print(f"Title: {result['title']}")
            print(f"Authors: {', '.join(result['authors']) if result['authors'] else 'N/A'}")
            print(f"Publish Date: {result['publish_date']}")
            print(f"Text Length: {len(result['text'])} characters")
            print(f"Summary Length: {len(result['summary'])} characters")
            print(f"Keywords: {len(result['keywords'])} keywords")
            print(f"{'='*70}")
            
            # Print first 500 characters of text
            if result['text']:
                print(f"\nFirst 500 characters of text:")
                print(f"{'-'*70}")
                print(result['text'][:500])
                print(f"{'-'*70}")
            
            # Print summary
            if result['summary']:
                print(f"\nSummary:")
                print(f"{'-'*70}")
                print(result['summary'])
                print(f"{'-'*70}")
            
            return result
            
        except Exception as e:
            print(f"\n✗ Extraction Failed!")
            print(f"Error: {str(e)}")
            
            return {
                'url': url,
                'title': '',
                'authors': [],
                'publish_date': None,
                'text': '',
                'summary': '',
                'keywords': [],
                'top_image': '',
                'extracted_at': datetime.now().isoformat(),
                'success': False,
                'error': str(e)
            }


def test_single_url():
    """Test extraction with a single URL"""
    extractor = SimpleArticleExtractor()
    
    # Test URL - replace with any article URL you want to test
    test_url = "https://www.siasat.com/delhi-mohammed-umardeen-shot-dead-while-trying-to-rescue-son-3371864/"
    
    result = extractor.extract_article_text(test_url)
    
    if result['success']:
        print(f"\n✓ Test Passed!")
    else:
        print(f"\n✗ Test Failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")


def test_multiple_urls():
    """Test extraction with multiple URLs"""
    extractor = SimpleArticleExtractor()
    
    # Test URLs - replace with actual article URLs
    test_urls = [
        "https://timesofindia.indiatimes.com/city/delhi/delhi-crime-news/articleshow/123456.cms",
        "https://indianexpress.com/article/cities/delhi/delhi-crime-news-123456/",
        "https://www.hindustantimes.com/cities/delhi-news/delhi-crime-news-123456.html"
    ]
    
    results = []
    success_count = 0
    
    print(f"\n{'='*70}")
    print(f"Testing {len(test_urls)} URLs")
    print(f"{'='*70}\n")
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n[{i}/{len(test_urls)}] Testing URL...")
        result = extractor.extract_article_text(url)
        results.append(result)
        
        if result['success']:
            success_count += 1
    
    # Summary
    print(f"\n{'='*70}")
    print(f"Test Summary")
    print(f"{'='*70}")
    print(f"Total URLs tested: {len(test_urls)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(test_urls) - success_count}")
    print(f"Success Rate: {(success_count/len(test_urls)*100):.1f}%")
    print(f"{'='*70}\n")
    
    return results


def test_with_custom_url():
    """Test with a custom URL provided by user"""
    extractor = SimpleArticleExtractor()
    
    print(f"\n{'='*70}")
    print(f"Custom URL Test")
    print(f"{'='*70}\n")
    
    url = input("Enter article URL to test: ").strip()
    
    if not url:
        print("No URL provided. Exiting.")
        return
    
    result = extractor.extract_article_text(url)
    
    return result


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                  Article Text Extractor - Test                      ║
║                  Same logic as backend/article_extractor.py          ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    print("Choose test mode:")
    print("1. Test with custom URL (enter your own)")
    print("2. Test with single predefined URL")
    print("3. Test with multiple predefined URLs")
    print("4. Exit")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        test_with_custom_url()
    elif choice == "2":
        test_single_url()
    elif choice == "3":
        test_multiple_urls()
    elif choice == "4":
        print("Exiting...")
    else:
        print("Invalid choice. Exiting...")
