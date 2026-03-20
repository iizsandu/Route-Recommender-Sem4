# Database Documentation

## MongoDB

**Connection:** `mongodb://localhost:27017/`  
**Database:** `crime2`

---

## Collections

### `articles` — Times of India

Stores articles scraped from Times of India Delhi pages.

```json
{
  "_id": "ObjectId",
  "url": "https://timesofindia.indiatimes.com/...",
  "title": "Man arrested for robbery in Dwarka",
  "date": "2026-03-15T00:00:00",
  "text": "Full article body text...",
  "summary": "NLP-generated summary...",
  "source": "Times of India",
  "extracted_at": "2026-03-18T10:30:00",
  "description": "",
  "full_text_extracted": true
}
```

### `articles2` — Google News + NewsData.io

Primary collection. Stores articles from Google News and NewsData.io.

```json
{
  "_id": "ObjectId",
  "url": "https://www.hindustantimes.com/...",
  "title": "Delhi Police arrests gang of 5",
  "date": "2026-03-14T00:00:00",
  "text": "Full article body text...",
  "summary": "NLP-generated summary...",
  "source": "Google News",
  "keyword": "Delhi crime",
  "extracted_at": "2026-03-18T10:30:00",
  "full_text_extracted": true
}
```

For NewsData.io articles, additional fields:
```json
{
  "source": "NewsData.io - hindustantimes",
  "published_date": "2026-03-14 08:30:00",
  "description": "Short description from API..."
}
```

### `youtube` — YouTube Transcriptions

Stores transcriptions from YouTube live streams and video downloads.

```json
{
  "_id": "ObjectId",
  "title": "AAJTAK Live News - 2026-03-18 10:30",
  "url": "https://www.youtube.com/@aajtak/live",
  "source": "YouTube Live - AAJTAK",
  "published_date": "2026-03-18T10:30:00",
  "description": "First 500 chars of transcription...",
  "extracted_at": "2026-03-18T10:30:00",
  "full_transcription": "Complete transcription text...",
  "language": "hi",
  "video_path": "news_videos/aajtak_20260318_103000.mp4",
  "audio_path": "news_videos/aajtak_20260318_103000.mp3",
  "duration": 60
}
```

---

## Indexes

All three collections get these indexes automatically when `DBHandler` connects:

```python
# Prevents duplicate URLs — enforced at DB level
create_index([("url", ASCENDING)], unique=True, sparse=True)

# For sorting articles by date
create_index([("extracted_at", ASCENDING)])
```

`sparse=True` on the unique index means documents without a `url` field are excluded from the uniqueness check (safe for edge cases).

---

## Duplicate Prevention

Duplicates are prevented at two levels:

1. **In-memory:** `seen_urls` set in `UnifiedExtractor` tracks URLs within a session
2. **Database level:** Unique index on `url` — any `insert_one` with a duplicate URL raises a `DuplicateKeyError`, which is caught and counted as a duplicate (not an error)

```python
# In save_articles():
except Exception as e:
    if "duplicate key error" in str(e).lower():
        duplicate_count += 1   # Silent skip
    else:
        errors.append(str(e))  # Real error
```

---

## Azure Cosmos DB (Crime Extraction Service)

Used by the separate `crime_extraction_service` to store structured crime records.

**Database:** `crime_db`  
**Container:** `structured_crimes`  
**Partition Key:** `/crime_type`

### Schema

```json
{
  "id": "uuid-v4",
  "crime_type": "murder",
  "description": "Man shot dead in Rohini",
  "location": {
    "city": "Delhi",
    "state": "Delhi",
    "country": "India",
    "address": "Rohini Sector 7"
  },
  "date_time": "2026-03-14T22:30:00",
  "victim_count": 1,
  "suspect_count": 2,
  "weapon_used": "firearm",
  "source_article_id": "mongodb-object-id",
  "extraction_confidence": 0.78,
  "created_at": "2026-03-18T10:30:00"
}
```

### Confidence Score

Calculated based on how many fields were successfully extracted:

```
confidence = filled_fields / total_fields
```

Fields counted: `crime_type`, `description`, `date_time`, `victim_count`, `suspect_count`, `weapon_used`, `location.city`, `location.state`, `location.country`, `location.address`

---

## Querying the Database

### Get article count per collection
```javascript
db.articles2.countDocuments()
db.articles.countDocuments()
db.youtube.countDocuments()
```

### Find articles with full text
```javascript
db.articles2.find({ full_text_extracted: true }).count()
```

### Find articles missing text
```javascript
db.articles2.find({
  $or: [
    { text: { $exists: false } },
    { text: "" },
    { text: null }
  ]
})
```

### Find articles by source
```javascript
db.articles2.find({ source: "Google News" })
db.articles2.find({ source: /NewsData/ })
```

### Check indexes
```javascript
db.articles2.getIndexes()
```
