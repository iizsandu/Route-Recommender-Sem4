# Gaps and Flaws — Data Extraction

This document covers the major gaps, flaws, and risks in the current data extraction pipeline.

---

## 1. Data Quality

### No language filtering on Google News
The `GoogleNews` library does not reliably filter by language. Even with `lang='en'`, Hindi and mixed-language articles slip through. These articles get stored with garbled or empty text since `newspaper3k` struggles to parse non-English content.

### `newspaper3k` is unreliable on modern news sites
Most major Indian news sites (TOI, HT, NDTV) are JavaScript-heavy. `newspaper3k` uses static HTML parsing — it frequently returns empty `text` fields for articles that render content via JS. This means a large portion of stored articles have `full_text_extracted: false` and empty `text`.

### No minimum quality gate before saving
Articles are saved to MongoDB even when `text` is empty, `title` is empty, or `full_text_extracted` is `false`. There is no filter that says "only save if text length > N characters". This pollutes the database with low-quality records.

### URL cleaning is incomplete
`clean_url()` only strips a fixed list of known tracking params (`&ved=`, `&usg=`, etc.). It misses:
- Query strings that are part of the actual URL (e.g., `?articleId=123`)
- Fragment identifiers (`#section`)
- Redirect wrappers (Google News wraps URLs in `https://news.google.com/rss/articles/...`)

Some stored URLs are still Google redirect URLs, not the actual article URLs.

---

## 2. Extraction Coverage

### Times of India scraper is shallow
The TOI extractor only scrapes anchor text from 4 static pages. It relies on crime keywords appearing in the link text, which misses most articles (headlines like "Man held in Rohini" don't contain the word "crime"). Actual yield is 5–15 articles per run.

### Google News returns 0 results frequently
The `GoogleNews` Python library is an unofficial scraper that breaks regularly when Google changes its HTML structure. The current codebase has no fallback when it returns 0 results — it just silently moves on.

### NewsData.io is limited to `/latest`
The free tier only supports the `/latest` endpoint — no date range filtering. This means every run fetches the same recent articles. After the first run, most of the 200 daily credits are wasted on duplicates that get rejected by the unique index.

### No RSS feed integration
RSS feeds (TOI, HT, Indian Express, NDTV all have them) would be far more reliable than scraping HTML or using unofficial libraries. None are currently used.

### No pagination on TOI
The TOI extractor hits each page once and stops. There is no pagination — it never goes to page 2, 3, etc. of topic pages.

---

## 3. Deduplication

### In-memory deduplication is lost on restart
`seen_urls` is stored in `extraction_progress.json`. If the file is deleted or corrupted, the entire deduplication history is lost and the next run re-fetches everything. The database unique index catches it, but wastes time and API credits re-processing known URLs.

### URL normalization is inconsistent
The same article can be stored under slightly different URLs:
- `https://example.com/article` vs `https://example.com/article/`
- `http://` vs `https://`
- With and without `www.`

These are treated as different URLs and both get inserted.

### No content-based deduplication
Two different URLs can point to the same article (syndicated content, AMP versions, print versions). There is no title or content hash check — only URL-based deduplication.

---

## 4. Reliability and Error Handling

### Extraction runs as a blocking HTTP request
`POST /articles/extract-all` is a synchronous FastAPI endpoint that runs for up to 2 hours. The HTTP connection stays open the entire time. Any network interruption between the frontend and backend kills the extraction silently. There is no background task, no job queue, and no way to check status mid-run.

### No retry logic on failed article fetches
If `newspaper3k` fails to download an article (timeout, 403, connection reset), it is marked `full_text_extracted: false` and never retried. There is no queue of failed URLs to retry later.

### `extraction_progress.json` is not atomic
Progress is saved by writing the entire JSON file. If the process crashes mid-write, the file is corrupted and the next run starts from scratch.

### Rate limiting is naive
Google News uses a random sleep of 2–5 seconds between pages. This is not based on any actual rate limit signal — it is a guess. If Google blocks the IP, the extractor just logs an error and moves on without any backoff strategy.

---

## 5. Architecture

### Extraction blocks the API server
The extraction runs in the same process as the FastAPI server. A 2-hour extraction run blocks one worker thread entirely. If `uvicorn` is running with a single worker (default), no other API requests can be served during extraction.

### No task status endpoint
Once extraction starts, there is no way to check progress from the frontend without looking at the backend terminal. The UI just shows "Extracting Articles..." with no progress indicator, article count, or ETA.

### `extraction_progress.json` and `google_news_progress.json` are separate
`UnifiedExtractor` uses `extraction_progress.json`. `GoogleNewsExtractor` (when called directly) uses `google_news_progress.json`. These are two separate seen-URL sets that can diverge, causing the same URLs to be processed by both.

### FFmpeg path is hardcoded to a local Windows path
`D:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe` is hardcoded as the primary fallback in `audio_extractor.py`, `speech_to_text.py`, and `youtube_extractor.py`. This will fail on any machine that is not the original developer's laptop.

---

## 6. Security and Configuration

### API keys are hardcoded fallbacks
If `.env` is missing, the system fails with an unhandled `ValueError`. There is no graceful degradation or clear startup error message telling the user exactly which key is missing.

### No input validation on API endpoints
`POST /youtube/extract-url` accepts any URL string with no validation. A malformed or malicious URL is passed directly to `yt-dlp` as a subprocess argument.

### MongoDB has no authentication
The connection string is `mongodb://localhost:27017/` with no username or password. Fine for local dev, but a security risk if the port is exposed.

---

## 7. Missing Features (for a complete data pipeline)

| Gap | Impact |
|-----|--------|
| No scheduler | Extraction must be triggered manually every time |
| No dedup by content hash | Syndicated articles stored multiple times |
| No article quality score | No way to filter low-quality records downstream |
| No source metadata | Can't tell which TOI page an article came from |
| No extraction metrics dashboard | No visibility into success rates per source |
| No alerting | No notification when extraction fails or yields 0 articles |
| No data validation schema | Any dict can be inserted into MongoDB |
