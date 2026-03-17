"""
Quick Test - Article Extractor
Automatically tests with a sample URL
"""
from newspaper import Article
from datetime import datetime

def clean_url(url):
    """Clean URL by removing tracking parameters"""
    if not url:
        return url
    
    # Remove common tracking parameters
    tracking_params = ['&ved=', '&usg=', '&sa=', '&source=', '&cd=', '&cad=']
    
    for param in tracking_params:
        if param in url:
            url = url.split(param)[0]
    
    return url

def test_article_extraction(url):
    """Test article extraction with a given URL"""
    # Clean URL first
    clean_url_result = clean_url(url)
    
    print(f"\n{'='*70}")
    print(f"Testing Article Extraction")
    print(f"{'='*70}")
    print(f"Original URL: {url}")
    if clean_url_result != url:
        print(f"Cleaned URL:  {clean_url_result}")
    print()
    
    try:
        # Create article object with cleaned URL
        article = Article(clean_url_result)
        
        # Download
        print("📥 Downloading article...")
        article.download()
        
        # Parse
        print("📄 Parsing article...")
        article.parse()
        
        # NLP
        print("🧠 Performing NLP...")
        article.nlp()
        
        # Results
        print(f"\n{'='*70}")
        print(f"✓ Extraction Successful!")
        print(f"{'='*70}")
        print(f"Title: {article.title}")
        print(f"Authors: {', '.join(article.authors) if article.authors else 'N/A'}")
        print(f"Publish Date: {article.publish_date}")
        print(f"Text Length: {len(article.text)} characters")
        print(f"Summary Length: {len(article.summary)} characters")
        print(f"Keywords: {len(article.keywords)} keywords")
        print(f"{'='*70}")
        
        # Show first 300 characters
        if article.text:
            print(f"\nFirst 300 characters:")
            print(f"{'-'*70}")
            print(article.text[:300] + "...")
            print(f"{'-'*70}")
        
        # Show summary
        if article.summary:
            print(f"\nSummary:")
            print(f"{'-'*70}")
            print(article.summary)
            print(f"{'-'*70}")
        
        print(f"\n✓ Test Passed!\n")
        return True
        
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"✗ Extraction Failed!")
        print(f"{'='*70}")
        print(f"Error: {str(e)}")
        print(f"{'='*70}\n")
        return False


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              Quick Article Extraction Test                          ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test with a real Times of India article
    test_url = "https://timesofindia.indiatimes.com/city/delhi/delhi-police-arrest-man-for-cheating-people-on-pretext-of-providing-jobs/articleshow/107234567.cms"
    
    print("Testing with Times of India article...")
    print("(This is a sample URL - replace with any article URL you want to test)\n")
    
    success = test_article_extraction(test_url)
    
    if success:
        print("✓ Article extraction is working correctly!")
        print("\nYou can now test with your own URLs by:")
        print("1. Edit quick_test.py and change the test_url variable")
        print("2. Or run: python test_article_extractor.py (for interactive mode)")
    else:
        print("✗ Article extraction failed. Check the error above.")
