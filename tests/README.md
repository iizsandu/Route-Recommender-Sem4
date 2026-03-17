# Article Extractor Tests

Simple test scripts to extract text from article URLs using the same logic as `backend/article_extractor.py`.

## Available Tools

### 1. Test Article Extractor
Test extraction logic with sample URLs.

### 2. Fix Empty Articles Tool (NEW)
Re-extract articles with empty text fields using the improved extractor.

---

## 1. Test Article Extractor

### Quick Start (Easiest)

### Windows Batch File
```bash
cd tests
run_test.bat
```

### Manual Commands
```bash
cd tests
..\backend\venv\Scripts\activate
python quick_test.py
```

This automatically tests with a sample URL and shows results!

## Setup

### Install Dependencies

```bash
cd tests
pip install -r requirements.txt
```

Or use the backend virtual environment (recommended):

```bash
cd tests
..\backend\venv\Scripts\activate
```

## Usage

### Option 1: Quick Test (Automatic)

```bash
python quick_test.py
```

Tests with a predefined URL and displays results immediately.

### Option 2: Interactive Test (More Options)

```bash
python test_article_extractor.py
```

### Test Modes

The script offers 4 test modes:

#### 1. Test with Custom URL (Recommended)
- Enter any article URL you want to test
- Extracts and displays full article content
- Shows title, authors, date, text, summary, keywords

#### 2. Test with Single Predefined URL
- Tests with a hardcoded Times of India URL
- Quick test to verify extraction works

#### 3. Test with Multiple Predefined URLs
- Tests with 3 different news sources
- Shows success rate
- Good for testing reliability

#### 4. Exit
- Exits the program

## What It Extracts

For each article URL, the extractor gets:

- **Title** - Article headline
- **Authors** - List of authors
- **Publish Date** - When article was published
- **Text** - Full article text content
- **Summary** - AI-generated summary
- **Keywords** - Extracted keywords
- **Top Image** - Main article image URL

## Example Output

```
======================================================================
Extracting: https://timesofindia.indiatimes.com/city/delhi/...
======================================================================
📥 Downloading article...
📄 Parsing article...
🧠 Performing NLP...

✓ Extraction Successful!
======================================================================
Title: Delhi police arrest four in connection with robbery case
Authors: John Doe, Jane Smith
Publish Date: 2025-01-15 10:30:00
Text Length: 2345 characters
Summary Length: 456 characters
Keywords: 5 keywords
======================================================================

First 500 characters of text:
----------------------------------------------------------------------
Delhi police on Tuesday arrested four people in connection with a 
robbery case. The accused were identified as...
----------------------------------------------------------------------

Summary:
----------------------------------------------------------------------
Delhi police arrested four individuals involved in a robbery case.
The arrests were made following a tip-off...
----------------------------------------------------------------------
```

## Testing Your Own URLs

### Option 1: Interactive Mode

```bash
python test_article_extractor.py
# Choose option 1
# Enter your URL when prompted
```

### Option 2: Edit the Script

Open `test_article_extractor.py` and modify the `test_single_url()` function:

```python
def test_single_url():
    extractor = SimpleArticleExtractor()
    
    # Replace with your URL
    test_url = "https://your-article-url-here.com"
    
    result = extractor.extract_article_text(test_url)
```

Then run:
```bash
python test_article_extractor.py
# Choose option 2
```

## Supported News Sources

The extractor works with most news websites including:

- Times of India
- Indian Express
- Hindustan Times
- NDTV
- The Hindu
- And many more...

## Troubleshooting

### Issue: "No module named 'newspaper'"

**Solution:**
```bash
pip install newspaper3k
```

### Issue: "No module named 'lxml'"

**Solution:**
```bash
pip install lxml
```

### Issue: Extraction fails for specific URL

**Possible causes:**
- Website blocks scraping
- Article behind paywall
- JavaScript-heavy site
- Invalid URL

**Solution:**
- Try a different article URL
- Check if URL is accessible in browser
- Some sites require authentication

### Issue: Empty text extracted

**Possible causes:**
- Article content in JavaScript
- Paywall blocking content
- Unusual HTML structure

**Solution:**
- Try articles from mainstream news sites
- Avoid paywalled content

## Logic Explanation

The extractor uses the same logic as `backend/article_extractor.py`:

1. **Download** - Fetches HTML content from URL
2. **Parse** - Extracts article structure from HTML
3. **NLP** - Generates summary and keywords using AI
4. **Return** - Returns structured data

### Code Flow

```python
article = Article(url)
article.download()  # Step 1: Download HTML
article.parse()     # Step 2: Parse content
article.nlp()       # Step 3: Generate summary/keywords

# Step 4: Extract data
result = {
    'url': url,
    'title': article.title,
    'text': article.text,
    'summary': article.summary,
    # ... more fields
}
```

## Use Cases

### 1. Test Article Extraction
- Verify extraction works for specific URLs
- Check text quality
- Test different news sources

### 2. Debug Extraction Issues
- See exactly what gets extracted
- Identify parsing problems
- Test edge cases

### 3. Validate URLs
- Check if URLs are extractable
- Verify content availability
- Test before adding to main system

## Notes

- This is a **test script** - simplified version for testing only
- Uses same extraction logic as production code
- No database integration (just prints results)
- No error recovery or retries
- Perfect for quick testing and debugging

## Next Steps

After testing URLs here:
1. Add working URLs to main extraction system
2. Use in `backend/article_extractor.py`
3. Run full extraction with `unified_extractor.py`

---

**Happy Testing!** 🧪


---

## 2. Fix Empty Articles Tool

### Purpose

Re-extracts articles from the database that have empty or missing text fields. These articles failed during initial extraction, often due to URL tracking parameters.

### Quick Start

**Windows Batch File:**
```bash
cd tests
fix_empty_articles.bat
```

**Python Command:**
```bash
cd tests
..\backend\venv\Scripts\activate
python fix_empty_articles.py
```

### Common Commands

**Check how many articles need fixing:**
```bash
python fix_empty_articles.py --check-only
```

**Fix first 10 articles (test run):**
```bash
python fix_empty_articles.py --limit 10
```

**Fix all empty articles:**
```bash
python fix_empty_articles.py
```

### What It Does

1. Finds articles with empty `text` field in `articles2` collection
2. Cleans URLs (removes `&ved=`, `&usg=`, etc.)
3. Re-extracts content using centralized extractor
4. Updates database with extracted content

### Example Output

```
🔍 Searching for articles with empty text...
✓ Found 156 articles with empty text

[1/156] Processing...
  Title: Delhi police arrest man...
  URL: https://example.com/article&ved=123
  Cleaned URL: https://example.com/article
  ✓ Success: Extracted 2345 characters
```

### For More Details

See **FIX_EMPTY_ARTICLES.md** for complete documentation including:
- All command line options
- Performance estimates
- Troubleshooting guide
- Best practices

---

## Files in This Folder

- `test_article_extractor.py` - Interactive article extraction tester
- `quick_test.py` - Quick automated test
- `run_test.bat` - Windows batch file for quick test
- `fix_empty_articles.py` - Tool to fix empty articles in database
- `fix_empty_articles.bat` - Windows batch file for fixer
- `README.md` - This file
- `FIX_EMPTY_ARTICLES.md` - Complete documentation for fixer tool
- `requirements.txt` - Python dependencies

---

**Happy Testing!** 🧪
