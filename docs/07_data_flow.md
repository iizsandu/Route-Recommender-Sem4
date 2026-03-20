# Data Flow

## Article Extraction Flow

```
User clicks "Extract Articles" in UI
        │
        ▼
frontend/services/api.js
extractArticles() → POST /articles/extract-all
        │
        ▼
backend/main.py
extract_all_articles()
        │
        ▼
backend/unified_extractor.py
UnifiedExtractor.extract_indefinitely(timeout_minutes=120)
        │
        ├── load_progress()
        │   └── Reads extraction_progress.json
        │       └── Restores seen_urls set (avoids re-fetching)
        │
        ├── CYCLE 1
        │   │
        │   ├── extract_from_google_news(keywords)
        │   │   │
        │   │   ├── GoogleNews(lang='en').search(keyword)
        │   │   ├── For each result URL:
        │   │   │   ├── clean_url() → strips &ved=, &usg=, etc.
        │   │   │   ├── Skip if in seen_urls
        │   │   │   ├── article_text_extractor.extract(url)
        │   │   │   │   └── newspaper3k: download → parse → nlp()
        │   │   │   └── Append to all_articles
        │   │   └── Auto-save every 50 articles
        │   │
        │   ├── extract_from_times_of_india(max_articles=100)
        │   │   │
        │   │   ├── GET https://timesofindia.indiatimes.com/city/delhi
        │   │   ├── GET https://timesofindia.indiatimes.com/topic/delhi-crime
        │   │   ├── GET https://timesofindia.indiatimes.com/topic/delhi-police
        │   │   ├── GET https://timesofindia.indiatimes.com/topic/delhi-murder
        │   │   ├── Filter links by crime keywords in anchor text
        │   │   ├── article_text_extractor.extract(url)
        │   │   └── Auto-save every 50 articles
        │   │
        │   └── extract_from_newsdata(max_credits=200)
        │       │
        │       ├── credit_manager.get_status() → check available credits
        │       ├── Rotate through 19 Delhi keywords
        │       ├── GET https://newsdata.io/api/1/latest?q=keyword&language=en&country=in
        │       ├── credit_manager.use_credits(1) per API call
        │       ├── article_text_extractor.extract(url) for each result
        │       └── Auto-save every 50 articles
        │
        ├── save_progress()
        │   ├── Write extraction_progress.json
        │   └── DBHandler("articles2").save_articles(all_articles)
        │       └── insert_one() per article
        │           └── DuplicateKeyError → silent skip (unique index)
        │
        ├── CYCLE 2, 3, ... (NewsData.io skipped after cycle 1)
        │
        └── Stop when: timeout | 0 new articles | 10 errors
```

---

## YouTube Extraction Flow

```
User pastes URL → clicks "Download & Transcribe"
        │
        ▼
POST /youtube/extract-url { url, language }
        │
        ▼
YouTubePipeline.process_youtube_url(url)
        │
        ├── STEP 1: YouTubeExtractor.download_video_from_url(url)
        │   └── yt-dlp downloads → news_videos/youtube_TIMESTAMP.mp4
        │
        ├── STEP 2: AudioExtractor.extract_audio(video_path)
        │   └── FFmpeg: MP4 → MP3 (192k)
        │       news_videos/youtube_TIMESTAMP.mp3
        │
        ├── STEP 3: SpeechToText.transcribe_file(audio_path)
        │   └── OpenAI Whisper (base model)
        │       Returns { text: "...", language: "hi" }
        │
        └── STEP 4: DBHandler("youtube").save_articles([article])
            └── Inserts into crime2.youtube
```

---

## Crime Extraction Flow (Separate Service)

```
POST /process-batch { limit: 50 }
        │
        ▼
processor.process_batch(limit=50)
        │
        ├── mongodb_client.get_articles(50)
        │   └── Fetches from crime2.articles2
        │
        └── For each article:
            │
            ├── LLMExtractor.extract_crime_info(text)
            │   │
            │   ├── RateLimiter.wait_if_needed()
            │   │   ├── llama3.1-8b available? → use it
            │   │   ├── llama at limit → try gpt-oss-120b
            │   │   └── both at limit → use Ollama
            │   │
            │   ├── POST https://api.cerebras.ai/v1/chat/completions
            │   │   └── Returns JSON with crime fields
            │   │
            │   └── Parse JSON → validate → build Crime object
            │
            ├── Crime.calculate_confidence()
            │   └── filled_fields / total_fields
            │
            └── CosmosDBClient.insert_crime_record(crime)
                └── Inserts into crime_db.structured_crimes
```

---

## URL Deduplication Flow

```
New URL arrives
        │
        ├── Check seen_urls (in-memory set)
        │   └── Already seen? → Skip immediately
        │
        ├── clean_url() → strip tracking params
        │
        └── DBHandler.save_articles()
            └── insert_one()
                └── DuplicateKeyError (unique index on url)?
                    ├── Yes → duplicate_count++, continue
                    └── No → inserted_count++
```

---

## Progress Resume Flow

```
Extraction starts
        │
        ├── os.path.exists("extraction_progress.json")?
        │   ├── Yes → load seen_urls from file
        │   │         (e.g., 2568 URLs from previous run)
        │   └── No → start fresh
        │
        └── All new URLs checked against seen_urls
            └── Already in set? → Skip (no HTTP request made)
```

This means if extraction is interrupted (crash, timeout, manual stop), the next run picks up where it left off without re-fetching already-processed URLs.
