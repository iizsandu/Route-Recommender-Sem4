# Crime Extraction Service

## What Is It?

A standalone FastAPI microservice (`crime_extraction_service/`) that reads raw articles from MongoDB, uses an LLM to determine if the article describes a crime, extracts structured information, and stores the result in Azure Cosmos DB.

This service is **separate** from the main backend. It runs independently and is not called by `backend/main.py`.

---

## How to Run

```bash
cd crime_extraction_service
venv\Scripts\activate
uvicorn app.main:app --reload --port 8001
```

API docs: http://localhost:8001/docs

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health + config info |
| GET | `/` | Root with endpoint list |
| POST | `/process-batch` | Process N articles from MongoDB |

### Process Batch Request

```json
POST /process-batch
{
  "limit": 50
}
```

Response:
```json
{
  "processed": 50,
  "successful": 38,
  "failed": 12,
  "errors": ["Article ID xyz: JSON parse error", "..."]
}
```

---

## Processing Flow

```
POST /process-batch { limit: 50 }
        │
        ▼
processor.process_batch(limit=50)
        │
        ├── mongodb_client.get_articles(limit=50)
        │   └── Fetches from crime2.articles2
        │
        └── For each article:
            │
            ├── llm_extractor.extract_crime_info(article_text)
            │   ├── Check rate limits (RateLimiter)
            │   ├── Try Cerebras API (llama3.1-8b or gpt-oss-120b)
            │   └── Fallback to Ollama if Cerebras fails
            │
            ├── validator.validate(extracted_data)
            │   └── Checks required fields, data types
            │
            └── cosmosdb_client.insert_crime_record(crime)
                └── Stores in crime_db.structured_crimes
```

---

## LLM Extraction

### Primary: Cerebras API

Two models available, automatically switched based on rate limits:

| Model | RPM | TPM | Use Case |
|-------|-----|-----|----------|
| `llama3.1-8b` | 30 | 60,000 | Default, fast |
| `gpt-oss-120b` | 30 | 64,000 | Fallback when llama hits limit |

### Fallback: Ollama (Local)

If both Cerebras models are rate-limited, the service falls back to a locally running Ollama instance. Default model: `llama3.2`.

### Rate Limiter Logic

```
Request comes in
    │
    ├── llama3.1-8b under limit? → Use llama
    │
    ├── llama at limit → Try gpt-oss-120b
    │   └── gpt-oss under limit? → Use gpt-oss
    │
    └── Both at limit → Use Ollama
```

### Extraction Prompt

```
You are an information extraction system.
Determine whether the article describes a real-world crime event.
Return ONLY valid JSON.

Schema:
{
  "crime_type": "murder/robbery/assault/theft/kidnapping/rape/burglary or null",
  "description": "brief crime description or null",
  "location": {
    "city": "string or null",
    "state": "string or null",
    "country": "string or null",
    "address": "string or null"
  },
  "date_time": "ISO 8601 or null",
  "victim_count": integer or null,
  "suspect_count": integer or null,
  "weapon_used": "string or null"
}
```

---

## Data Models

### Crime (Pydantic)

```python
class Crime(BaseModel):
    id: str                          # UUID v4
    crime_type: Optional[str]        # murder/robbery/etc
    description: Optional[str]
    location: Optional[Location]
    date_time: Optional[datetime]
    victim_count: Optional[int]
    suspect_count: Optional[int]
    weapon_used: Optional[str]
    source_article_id: str           # MongoDB article _id
    extraction_confidence: float     # 0.0 to 1.0
    created_at: datetime
```

### Location (Pydantic)

```python
class Location(BaseModel):
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    address: Optional[str]
```

---

## Configuration (`app/config.py`)

All settings loaded from `crime_extraction_service/.env`:

```python
cerebras_api_key: str
cerebras_api_url: str = "https://api.cerebras.ai/v1/chat/completions"
cosmos_endpoint: str
cosmos_key: str
cosmos_database: str = "crime_db"
cosmos_container: str = "structured_crimes"
mongodb_url: str = "mongodb://localhost:27017/"
mongodb_database: str = "crime2"
mongodb_collection: str = "articles2"
ollama_model: str = "llama3.2"
ollama_url: str = "http://localhost:11434"
```

---

## Logging

Uses `structlog` for structured JSON logging. All log entries include:
- Timestamp
- Log level
- Event name (e.g., `extraction_started`, `crime_inserted`)
- Contextual fields (model used, article ID, confidence, etc.)

Example log output:
```json
{"event": "crime_inserted", "crime_id": "abc-123", "crime_type": "murder", "confidence": 0.78, "level": "info"}
```
