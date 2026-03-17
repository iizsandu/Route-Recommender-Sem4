# Execution Flow - Crime Extraction Service

## Complete Data Flow

### Step-by-Step Execution

```
USER REQUEST
    ↓
POST /process-batch {"limit": 10}
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. FETCH FROM MONGODB                                           │
│    Collection: crime2.articles2                                 │
│    Query: {text: {$exists: true, $ne: ""}}                     │
│    Limit: 10                                                    │
│                                                                  │
│    Returns:                                                      │
│    [                                                             │
│      {                                                           │
│        "_id": "65abc123...",                                    │
│        "url": "https://timesofindia.com/...",                  │
│        "title": "Delhi police arrest man...",                  │
│        "text": "Delhi police on Tuesday arrested a man..."     │
│      },                                                          │
│      ... 9 more articles                                        │
│    ]                                                             │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. FOR EACH ARTICLE (Loop through 10 articles)                 │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. EXTRACT WITH LLM                                             │
│                                                                  │
│    Input to LLM:                                                │
│    ┌──────────────────────────────────────────────────────┐   │
│    │ System Prompt:                                        │   │
│    │ "Extract structured crime information..."            │   │
│    │ Schema: {crime_type, description, location, ...}     │   │
│    │                                                        │   │
│    │ User Message:                                         │   │
│    │ "Extract crime information:                          │   │
│    │                                                        │   │
│    │ Delhi police on Tuesday arrested a man for           │   │
│    │ allegedly cheating people on the pretext of          │   │
│    │ providing them jobs. The accused was identified      │   │
│    │ as Rajesh Kumar, 35, a resident of Rohini.          │   │
│    │ Police said they received multiple complaints..."    │   │
│    └──────────────────────────────────────────────────────┘   │
│                                                                  │
│    Rate Limiter checks:                                         │
│    - llama3.1-8b: 5 requests in last minute → OK              │
│    - Estimated tokens: 1500 → OK                               │
│    → Use llama3.1-8b                                           │
│                                                                  │
│    API Call to Cerebras:                                        │
│    POST https://api.cerebras.ai/v1/chat/completions            │
│    {                                                             │
│      "model": "llama3.1-8b",                                   │
│      "messages": [...],                                         │
│      "temperature": 0.0,                                        │
│      "max_tokens": 1000                                         │
│    }                                                             │
│                                                                  │
│    LLM Response:                                                │
│    ┌──────────────────────────────────────────────────────┐   │
│    │ {                                                     │   │
│    │   "crime_type": "fraud",                             │   │
│    │   "description": "Man arrested for job fraud",       │   │
│    │   "location": {                                       │   │
│    │     "city": "Delhi",                                  │   │
│    │     "state": "Delhi",                                 │   │
│    │     "country": "India",                               │   │
│    │     "address": "Rohini"                               │   │
│    │   },                                                   │   │
│    │   "date_time": "2024-02-27T10:00:00",               │   │
│    │   "victim_count": null,                               │   │
│    │   "suspect_count": 1,                                 │   │
│    │   "weapon_used": null                                 │   │
│    │ }                                                     │   │
│    └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. VALIDATE WITH PYDANTIC                                       │
│                                                                  │
│    Input: LLM response dict + source_article_id                │
│                                                                  │
│    Validation Steps:                                            │
│    1. Parse location into Location model                        │
│    2. Create Crime model with all fields                        │
│    3. Calculate confidence score                                │
│                                                                  │
│    Confidence Calculation:                                      │
│    - Total possible fields: 9                                   │
│    - Filled fields:                                             │
│      ✓ crime_type (fraud)                                      │
│      ✓ description                                              │
│      ✓ location.city (Delhi)                                   │
│      ✓ location.state (Delhi)                                  │
│      ✓ location.country (India)                                │
│      ✓ location.address (Rohini)                               │
│      ✓ date_time                                                │
│      ✗ victim_count (null)                                     │
│      ✓ suspect_count (1)                                       │
│      ✗ weapon_used (null)                                      │
│    - Confidence: 7/9 = 0.78                                     │
│                                                                  │
│    Validated Crime Object:                                      │
│    ┌──────────────────────────────────────────────────────┐   │
│    │ Crime(                                                │   │
│    │   id="a1b2c3d4-...",                                 │   │
│    │   crime_type="fraud",                                │   │
│    │   description="Man arrested for job fraud",          │   │
│    │   location=Location(                                  │   │
│    │     city="Delhi",                                     │   │
│    │     state="Delhi",                                    │   │
│    │     country="India",                                  │   │
│    │     address="Rohini"                                  │   │
│    │   ),                                                   │   │
│    │   date_time=datetime(2024, 2, 27, 10, 0, 0),        │   │
│    │   victim_count=None,                                  │   │
│    │   suspect_count=1,                                    │   │
│    │   weapon_used=None,                                   │   │
│    │   source_article_id="65abc123...",                   │   │
│    │   extraction_confidence=0.78,                         │   │
│    │   created_at=datetime.utcnow()                        │   │
│    │ )                                                     │   │
│    └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. STORE IN COSMOS DB                                           │
│                                                                  │
│    Convert to dict:                                             │
│    crime_dict = crime.model_dump(mode='json')                  │
│                                                                  │
│    Ensure partition key:                                        │
│    if not crime_dict['crime_type']:                            │
│        crime_dict['crime_type'] = 'unknown'                    │
│                                                                  │
│    Insert into Cosmos DB:                                       │
│    ┌──────────────────────────────────────────────────────┐   │
│    │ Database: crime_db                                    │   │
│    │ Container: structured_crimes                          │   │
│    │ Partition Key: /crime_type                           │   │
│    │                                                        │   │
│    │ Document:                                             │   │
│    │ {                                                     │   │
│    │   "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",     │   │
│    │   "crime_type": "fraud",                             │   │
│    │   "description": "Man arrested for job fraud",       │   │
│    │   "location": {                                       │   │
│    │     "city": "Delhi",                                  │   │
│    │     "state": "Delhi",                                 │   │
│    │     "country": "India",                               │   │
│    │     "address": "Rohini"                               │   │
│    │   },                                                   │   │
│    │   "date_time": "2024-02-27T10:00:00",               │   │
│    │   "victim_count": null,                               │   │
│    │   "suspect_count": 1,                                 │   │
│    │   "weapon_used": null,                                │   │
│    │   "source_article_id": "65abc123...",               │   │
│    │   "extraction_confidence": 0.78,                     │   │
│    │   "created_at": "2024-02-27T15:30:45.123Z"          │   │
│    │ }                                                     │   │
│    └──────────────────────────────────────────────────────┘   │
│                                                                  │
│    Cosmos DB stores in partition: fraud                         │
└─────────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. MARK AS PROCESSED IN MONGODB                                │
│                                                                  │
│    Update MongoDB:                                              │
│    db.articles2.update_one(                                     │
│      {"_id": "65abc123..."},                                   │
│      {"$set": {"processed": true}}                             │
│    )                                                             │
└─────────────────────────────────────────────────────────────────┘
    ↓
REPEAT FOR REMAINING 9 ARTICLES
    ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. RETURN STATISTICS                                            │
│                                                                  │
│    {                                                             │
│      "processed": 10,                                           │
│      "successful": 8,                                           │
│      "failed": 2,                                               │
│      "errors": [                                                │
│        "Extraction failed for article 65xyz...",               │
│        "Validation failed for article 65abc..."                │
│      ]                                                           │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Real Example with Your Data

### Input: Article from MongoDB

```javascript
// From crime2.articles2 collection
{
  "_id": ObjectId("65abc123def456789"),
  "url": "https://timesofindia.indiatimes.com/city/delhi/...",
  "title": "Delhi: Man arrested for cheating job seekers",
  "text": "Delhi police on Tuesday arrested a 35-year-old man for allegedly cheating people on the pretext of providing them jobs. The accused was identified as Rajesh Kumar, a resident of Rohini. Police said they received multiple complaints from victims who had paid Rs 50,000 each to Kumar for government jobs that never materialized. The arrest was made following a raid at his residence in Rohini sector 15.",
  "source": "Times of India",
  "extracted_at": "2024-02-27T10:00:00"
}
```

### Processing Steps

**Step 1: Extract article text**
```python
article_text = article["text"]
article_id = str(article["_id"])
```

**Step 2: Send to LLM**
```python
# Rate limiter checks and selects model
model = await rate_limiter.wait_if_needed(estimated_tokens=1500)
# Returns: "llama3.1-8b"

# Call Cerebras API
response = await client.post(
    "https://api.cerebras.ai/v1/chat/completions",
    json={
        "model": "llama3.1-8b",
        "messages": [
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": f"Extract crime information:\n\n{article_text}"}
        ],
        "temperature": 0.0
    }
)
```

**Step 3: LLM Returns JSON**
```json
{
  "crime_type": "fraud",
  "description": "Man arrested for cheating job seekers by promising government jobs",
  "location": {
    "city": "Delhi",
    "state": "Delhi",
    "country": "India",
    "address": "Rohini sector 15"
  },
  "date_time": "2024-02-27T10:00:00",
  "victim_count": null,
  "suspect_count": 1,
  "weapon_used": null
}
```

**Step 4: Validate with Pydantic**
```python
crime = Crime(
    id=str(uuid4()),  # "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    crime_type="fraud",
    description="Man arrested for cheating job seekers...",
    location=Location(
        city="Delhi",
        state="Delhi",
        country="India",
        address="Rohini sector 15"
    ),
    date_time=datetime(2024, 2, 27, 10, 0, 0),
    victim_count=None,
    suspect_count=1,
    weapon_used=None,
    source_article_id="65abc123def456789",
    extraction_confidence=0.78  # 7 out of 9 fields filled
)
```

**Step 5: Store in Cosmos DB**
```python
# Convert to dict
crime_dict = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "crime_type": "fraud",
    "description": "Man arrested for cheating job seekers...",
    "location": {
        "city": "Delhi",
        "state": "Delhi",
        "country": "India",
        "address": "Rohini sector 15"
    },
    "date_time": "2024-02-27T10:00:00",
    "victim_count": None,
    "suspect_count": 1,
    "weapon_used": None,
    "source_article_id": "65abc123def456789",
    "extraction_confidence": 0.78,
    "created_at": "2024-02-27T15:30:45.123Z"
}

# Insert into Cosmos DB
await container.create_item(body=crime_dict)
```

**Step 6: Cosmos DB Storage**
```
Database: crime_db
Container: structured_crimes
Partition: fraud (from crime_type field)

Document stored with:
- Unique id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
- Partition key: fraud
- All crime fields
- Queryable by any field
```

## Rate Limiting in Action

### Scenario: Processing 100 Articles

```
Article 1-30:  llama3.1-8b (fast, 8K context)
               ↓ (30 requests in 1 minute - limit reached)
Article 31-60: gpt-oss-120b (better quality, 65K context)
               ↓ (30 requests in 1 minute - limit reached)
Article 61-100: Ollama local (unlimited, free)
```

### Rate Limiter Logic

```python
# Before each request
model = await rate_limiter.wait_if_needed(estimated_tokens=2000)

# Rate limiter checks:
# 1. Count llama3.1-8b requests in last minute: 28 < 30 ✓
# 2. Count llama3.1-8b tokens in last minute: 56000 < 60000 ✓
# 3. Add 2000 tokens: 58000 < 60000 ✓
# → Use llama3.1-8b

# Next request (30th):
# 1. Count llama3.1-8b requests: 29 < 30 ✓
# 2. Count tokens: 58000 + 2000 = 60000 = 60000 ✓
# → Use llama3.1-8b

# Next request (31st):
# 1. Count llama3.1-8b requests: 30 = 30 ✗
# 2. Switch to gpt-oss-120b
# 3. Count gpt-oss-120b requests: 0 < 30 ✓
# → Use gpt-oss-120b
```

## Querying Cosmos DB

### After Processing

```python
# Query all fraud crimes
SELECT * FROM c WHERE c.crime_type = 'fraud'

# Query by location
SELECT * FROM c WHERE c.location.city = 'Delhi'

# Query by confidence
SELECT * FROM c WHERE c.extraction_confidence > 0.7

# Query by date range
SELECT * FROM c 
WHERE c.date_time >= '2024-01-01' 
AND c.date_time < '2024-02-01'

# Get statistics
SELECT 
    c.crime_type,
    COUNT(1) as count,
    AVG(c.extraction_confidence) as avg_confidence
FROM c
GROUP BY c.crime_type
```

## Complete Code Flow

```python
# In processor.py
async def process_batch(limit=10):
    # 1. Fetch from MongoDB
    articles = await mongodb_client.fetch_unprocessed_articles(limit)
    
    for article in articles:
        article_id = str(article["_id"])
        article_text = article["text"]
        
        # 2. Extract with LLM
        extracted_data = await extractor.extract_crime_info(article_text)
        
        # 3. Validate
        crime = await validator.validate_crime(extracted_data, article_id)
        
        # 4. Store in Cosmos DB
        success = await cosmosdb_client.insert_crime_record(crime)
        
        # 5. Mark as processed
        if success:
            await mongodb_client.mark_article_processed(article_id)
```

## Summary

1. **MongoDB** → Fetch article text
2. **Rate Limiter** → Choose best available model
3. **Cerebras/Ollama** → Extract structured JSON
4. **Pydantic** → Validate and calculate confidence
5. **Cosmos DB** → Store structured crime
6. **MongoDB** → Mark article as processed

The entire flow is async, handles errors gracefully, and never hits rate limits!
