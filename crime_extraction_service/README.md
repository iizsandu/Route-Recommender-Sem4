venv/Scriptsaction Service

Production microservice for extracting structured crime information from articles using Cerebras API with Ollama fallback.

## Documentation

- **README.md** - This file (quick start and overview)
- **SETUP.md** - Detailed setup instructions
- **EXECUTION_FLOW.md** - Step-by-step execution flow with examples
- **SYSTEM_DIAGRAM.md** - Visual architecture and data flow diagrams

## Quick Start

```bash
cd crime_extraction_service

# 1. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 2. Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Run service
uvicorn app.main:app --reload
```

## Configuration (.env)

```env
# MongoDB (your existing setup)
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=crime2
MONGODB_COLLECTION=articles2

# Azure Cosmos DB
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DATABASE=crime_db
COSMOS_CONTAINER=structured_crimes

# Cerebras API
CEREBRAS_API_KEY=your-cerebras-key
CEREBRAS_API_URL=https://api.cerebras.ai/v1/chat/completions

# Ollama (fallback - install from https://ollama.ai)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

## LLM Strategy

### Primary: Cerebras API
- **llama3.1-8b**: 8K context, 30 req/min, 60K tokens/min
- **gpt-oss-120b**: 65K context, 30 req/min, 64K tokens/min

Auto-switches between models to avoid rate limits.

### Fallback: Ollama (Local)
When both Cerebras models hit rate limits, automatically falls back to local Ollama.

Install Ollama:
```bash
# Download from https://ollama.ai
ollama pull llama3.1:8b
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Process Batch
```bash
POST /process-batch
Content-Type: application/json

{
  "limit": 10
}
```

Response:
```json
{
  "processed": 10,
  "successful": 8,
  "failed": 2,
  "errors": []
}
```

## Crime Schema

```json
{
  "id": "uuid",
  "crime_type": "murder",
  "description": "Brief description",
  "location": {
    "city": "Delhi",
    "state": "Delhi",
    "country": "India",
    "address": "Specific address"
  },
  "date_time": "2024-01-15T10:30:00",
  "victim_count": 1,
  "suspect_count": 2,
  "weapon_used": "knife",
  "source_article_id": "mongodb_article_id",
  "extraction_confidence": 0.85
}
```

## Usage

```bash
# Process 10 articles
curl -X POST http://localhost:8000/process-batch \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# Process 50 articles
curl -X POST http://localhost:8000/process-batch \
  -H "Content-Type: application/json" \
  -d '{"limit": 50}'
```

## Docker Deployment

```bash
# Build
docker build -t crime-extraction-service .

# Run
docker run -p 8000:8000 --env-file .env crime-extraction-service

# Or use docker-compose
docker-compose up -d
```

## Architecture

```
MongoDB (articles2) 
    ↓
Cerebras API (llama3.1-8b / gpt-oss-120b)
    ↓ (rate limit fallback)
Ollama (local llama3.1:8b)
    ↓
Pydantic Validation
    ↓
Cosmos DB (structured_crimes)
```

## Features

✓ Intelligent rate limiting (never hits Cerebras limits)
✓ Auto-switching between llama3.1-8b and gpt-oss-120b
✓ Automatic fallback to local Ollama
✓ Async architecture (FastAPI + Motor + Azure SDK)
✓ Pydantic validation with confidence scoring
✓ Structured JSON logging
✓ Production-ready (Docker, health checks)

## Troubleshooting

### Cerebras API Errors
- Check API key in .env
- Verify API URL
- Check rate limits in logs

### Ollama Not Working
```bash
# Install Ollama
# Download from https://ollama.ai

# Pull model
ollama pull llama3.1:8b

# Test
ollama run llama3.1:8b "Hello"
```

### MongoDB Connection Failed
```bash
# Check MongoDB is running
mongosh --eval "db.adminCommand('ping')"
```

### Cosmos DB Connection Failed
- Verify endpoint and key in Azure Portal
- Check firewall rules

## Performance

- **Throughput**: 10-30 articles/minute (depends on model)
- **Latency**: 1-3 seconds per article
- **Cost**: Free with Cerebras API (rate limited)

## License

MIT
