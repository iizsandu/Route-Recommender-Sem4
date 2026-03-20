# Backend Documentation

## Entry Point: `main.py`

FastAPI application running on port `8000`. Initializes three core objects on startup:

```python
article_extractor = ArticleExtractor()   # TOI extractor
db_handler = DBHandler()                  # MongoDB (articles collection)
youtube_pipeline = YouTubePipeline()      # YouTube pipeline
```

---

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{"status": "ok"}` |

### Article Stats

| Method | Path | Description |
|--------|------|-------------|
| GET | `/articles/stats` | Returns count from both `articles` and `articles2` collections |
| GET | `/articles2` | Paginated list from `articles2` collection |

### Extraction

| Method | Path | Description |
|--------|------|-------------|
| POST | `/articles/extract-all` | Run all 3 extraction methods (default 120 min timeout) |
| POST | `/articles/extract-google-news` | Google News only (default 60 min timeout) |
| POST | `/articles/extract-times-of-india` | Times of India only (default 200 articles) |
| POST | `/articles/extract-newsdata` | NewsData.io only (uses available credits) |
| GET | `/articles/newsdata-credits` | Current NewsData.io credit status |

### YouTube

| Method | Path | Description |
|--------|------|-------------|
| GET | `/youtube/channels` | List of available news channels |
| POST | `/youtube/extract` | Extract from a live channel stream |
| POST | `/youtube/extract-url` | Download and transcribe any YouTube video URL |

---

## Module: `db_handler.py`

Handles all MongoDB operations. Uses `pymongo`.

**Database:** `crime2`  
**Default collection:** `articles`

### Key Methods

```python
DBHandler(collection_name="articles2")  # Connect to specific collection

db.save_articles(articles)     # Insert with duplicate detection
db.get_articles(limit, skip)   # Paginated fetch, sorted by extracted_at DESC
db.get_article_count()         # Total document count
db.update_article_content(url, content)  # Update existing article
db.get_articles_without_full_text()      # Find articles missing text
```

### Indexes (auto-created on connect)

```python
# Unique index prevents duplicate URLs
create_index([("url", ASCENDING)], unique=True, sparse=True)

# For sorting by date
create_index([("extracted_at", ASCENDING)])
```

`sparse=True` means documents without a `url` field don't conflict on the unique constraint.

---

## Module: `article_text_extractor.py`

**Centralized extraction API.** Every article URL must pass through this before being saved to the database.

Uses `newspaper3k` under the hood.

### Key Methods

```python
extractor = get_extractor()  # Singleton instance

result = extractor.extract(url, source="Google News", keyword="Delhi crime")
# Returns standardized dict:
# {
#   'url': str,               # Cleaned URL
#   'title': str,
#   'text': str,              # Full article body
#   'summary': str,           # NLP summary
#   'publish_date': datetime,
#   'full_text_extracted': bool,
#   'extracted_at': str,      # ISO timestamp
#   'error': str or None
# }

clean_url = extractor.clean_url(url)
# Strips tracking params: &ved=, &usg=, &utm_*, &fbclid=, etc.
```

### Why Centralized?

Before this, each extractor had its own text extraction logic. Centralizing it means:
- URL cleaning happens in one place
- Data schema is consistent across all sources
- Errors are handled uniformly

---

## Module: `unified_extractor.py`

Orchestrates all three extraction methods in sequence. Called by the `/articles/extract-all` endpoint.

### How It Works

```
UnifiedExtractor.extract_indefinitely(timeout_minutes=120)
    ├── load_progress()           # Resume from extraction_progress.json
    ├── CYCLE 1
    │   ├── extract_from_google_news(keywords, pages=10)
    │   ├── extract_from_times_of_india(max_articles=100)
    │   └── extract_from_newsdata(max_credits=200)  # Only cycle 1
    ├── CYCLE 2
    │   ├── extract_from_google_news(...)
    │   └── extract_from_times_of_india(...)
    └── ... until timeout or 0 new articles
```

### Auto-Save

Every 50 articles (`auto_save_interval`), progress is saved to:
1. `backend/extraction_progress.json` — for resuming
2. MongoDB `crime2.articles2` — permanent storage

### Stop Conditions

- Timeout reached
- 10 consecutive errors (`max_errors`)
- Cycle produces 0 new articles

### Progress File Format

```json
{
  "articles": [],
  "seen_urls": ["https://...", "https://..."],
  "total_articles": 2568,
  "saved_at": "2026-03-18T10:30:00",
  "error_count": 0
}
```

---

## Module: `toi_extractor.py`

Scrapes Times of India Delhi pages for crime articles.

### Pages Scraped

```python
toi_delhi_urls = [
    "https://timesofindia.indiatimes.com/city/delhi",
    "https://timesofindia.indiatimes.com/topic/delhi-crime",
    "https://timesofindia.indiatimes.com/topic/delhi-police",
    "https://timesofindia.indiatimes.com/topic/delhi-murder",
]
```

### Keyword Filter

Only links whose anchor text contains one of these keywords are extracted:

```python
crime_keywords = [
    'crime', 'murder', 'robbery', 'theft', 'assault', 'rape', 'kidnapping',
    'arrested', 'held', 'killed', 'dead', 'body', 'attack', 'shot', 'stabbed',
    'police', 'accused', 'victim', 'gang', 'fraud', 'scam', 'burglary', 'loot'
]
```

---

## Module: `google_news_extractor.py`

Uses the `GoogleNews` Python library to search for articles by keyword.

### Keywords (Delhi-focused)

```python
"Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft",
"Delhi assault", "Delhi rape", "Delhi kidnapping", "Delhi burglary",
"Delhi police arrest", "Delhi gang", "Delhi violence", "Delhi shooting",
"Delhi stabbing", "Delhi fraud", "Delhi scam", "Delhi loot",
"New Delhi crime", "NCR crime", "Noida crime", "Gurga
on crime", "Faridabad crime",
"Dwarka crime", "Rohini crime", "Shahdara crime"
```

### Rate Limiting

- Random sleep of 2–5 seconds between pages
- 10 second wait on page errors
- Stops after 10 consecutive errors

### Progress File

Saves to `backend/google_news_progress.json` independently (separate from unified extractor's progress file).

---

## Module: `newsdata_extractor.py`

Fetches articles from the NewsData.io `/latest` API endpoint.

### Free Tier Constraints

- 200 credits per 24 hours
- 10 articles per credit
- Max 2000 articles per day
- Only `/latest` endpoint (no date range filtering)
- English + India (`language=en`, `country=in`)

### Credit Rotation

Keywords are rotated round-robin across all 200 credits to maximize diversity:

```
Credit 1 → "Delhi crime"
Credit 2 → "Delhi murder"
Credit 3 → "Delhi robbery"
...
Credit 19 → "Gurgaon crime"
Credit 20 → "Delhi crime"  (wraps around)
```

### Rate Limit Handling

If a 429 response is received, waits 60 seconds and retries.

---

## Module: `newsdata_credit_manager.py`

Tracks NewsData.io API credit usage locally in `backend/newsdata_credits.json`.

### Credit File Format

```json
{
  "credits_remaining": 150,
  "credits_used": 50,
  "last_reset": "2026-03-18T08:00:00",
  "next_reset": "2026-03-19T08:00:00",
  "last_used": "2026-03-18T10:30:00"
}
```

### Auto-Reset

On every `get_status()` call, if `datetime.now() >= next_reset`, credits are automatically reset to 200.

---

## Module: `youtube_pipeline.py`

Orchestrates the full YouTube extraction pipeline.

### Pipeline Steps

```
1. YouTubeExtractor.extract_live_stream(channel, duration)
   └── yt-dlp downloads video → news_videos/channel_timestamp.mp4

2. AudioExtractor.extract_audio(video_path)
   └── FFmpeg converts MP4 → MP3 (192k)

3. SpeechToText.transcribe_file(audio_path)
   └── OpenAI Whisper transcribes → text

4. DBHandler.save_articles([article])
   └── Saves to crime2.youtube collection
```

### Supported Channels

```python
channels = {
    "aajtak":   "https://www.youtube.com/@aajtak/live",
    "abpnews":  "https://www.youtube.com/@abpnewstv/live",
    "indiatv":  "https://www.youtube.com/@indiatvnews/live",
    "ndtv":     "https://www.youtube.com/@ndtv/live",
    "zeenews":  "https://www.youtube.com/@zeenews/live",
    "republic": "https://www.youtube.com/@RepublicWorld/live",
}
```

### Whisper Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 39MB | Fastest | Low |
| base | 74MB | Fast | Good (default) |
| small | 244MB | Medium | Better |
| medium | 769MB | Slow | High |
| large | 1.5GB | Slowest | Best |
