# Setup Guide

## Prerequisites

1. **Python 3.11+**
2. **MongoDB** (already running with crime2 database)
3. **Azure Cosmos DB** account
4. **Cerebras API** key
5. **Ollama** (optional, for fallback)

## Step 1: Get Cerebras API Key

1. Sign up at https://cerebras.ai
2. Get your API key from dashboard
3. Note: Free tier with rate limits (30 req/min)

## Step 2: Setup Azure Cosmos DB

```bash
# Create Cosmos DB account
az cosmosdb create \
  --name crime-cosmos-db \
  --resource-group your-rg \
  --default-consistency-level Session

# Create database
az cosmosdb sql database create \
  --account-name crime-cosmos-db \
  --resource-group your-rg \
  --name crime_db

# Create container
az cosmosdb sql container create \
  --account-name crime-cosmos-db \
  --resource-group your-rg \
  --database-name crime_db \
  --name structured_crimes \
  --partition-key-path "/crime_type" \
  --throughput 400

# Get connection details
az cosmosdb show --name crime-cosmos-db --resource-group your-rg --query documentEndpoint
az cosmosdb keys list --name crime-cosmos-db --resource-group your-rg --query primaryMasterKey
```

## Step 3: Install Ollama (Optional Fallback)

```bash
# Download from https://ollama.ai
# Then pull model:
ollama pull llama3.1:8b
```

## Step 4: Configure Service

```bash
cd crime_extraction_service
cp .env.example .env
```

Edit `.env`:
```env
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=crime2
MONGODB_COLLECTION=articles2

COSMOS_ENDPOINT=https://crime-cosmos-db.documents.azure.com:443/
COSMOS_KEY=your-key-here

CEREBRAS_API_KEY=your-cerebras-key-here

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

## Step 5: Run Service

### Windows
```bash
start.bat
```

### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

## Step 6: Test

```bash
# Health check
curl http://localhost:8000/health

# Process 5 articles (test)
curl -X POST http://localhost:8000/process-batch \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

## Rate Limiting Strategy

The service intelligently manages Cerebras API rate limits:

1. **Starts with llama3.1-8b** (8K context, faster)
2. **Switches to gpt-oss-120b** when llama hits limit (65K context, better quality)
3. **Falls back to Ollama** when both hit limits (local, unlimited)

Rate limits per minute:
- llama3.1-8b: 30 requests, 60K tokens
- gpt-oss-120b: 30 requests, 64K tokens

The service tracks usage and automatically switches models to never hit rate limits.

## Verify Cosmos DB

```bash
# Using Azure CLI
az cosmosdb sql container query \
  --account-name crime-cosmos-db \
  --resource-group your-rg \
  --database-name crime_db \
  --name structured_crimes \
  --query-text "SELECT * FROM c OFFSET 0 LIMIT 10"
```

Or use Azure Portal → Data Explorer.

## Troubleshooting

### "Cerebras API key invalid"
- Check key in .env
- Verify at https://cerebras.ai/dashboard

### "Ollama connection refused"
- Install Ollama from https://ollama.ai
- Run: `ollama serve`
- Pull model: `ollama pull llama3.1:8b`

### "MongoDB connection failed"
- Check MongoDB is running: `mongosh --eval "db.adminCommand('ping')"`

### "Cosmos DB unauthorized"
- Verify endpoint and key in Azure Portal
- Check firewall rules (allow your IP)

## Production Deployment

```bash
# Build Docker image
docker build -t crime-extraction-service .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Next Steps

1. Process your 1290 articles from articles2 collection
2. Monitor extraction confidence scores
3. Review extracted crimes in Cosmos DB
4. Adjust batch size based on performance

---

Service is ready! 🚀
