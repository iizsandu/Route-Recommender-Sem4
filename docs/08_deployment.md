# Deployment Guide

## Overview

The project has two deployable services:

| Service | Directory | Port | Purpose |
|---------|-----------|------|---------|
| Main Backend | `backend/` | 8000 | Article collection API |
| Frontend | `frontend/` | 3000 (dev) / static (prod) | Web UI |
| Crime Extraction | `crime_extraction_service/` | 8001 | LLM extraction (optional) |

---

## Environment Variables

### `backend/.env`

```env
NEWSDATA_API_KEY=your_key_here
```

### `crime_extraction_service/.env`

```env
CEREBRAS_API_KEY=your_key_here
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE=crime_db
COSMOS_CONTAINER=structured_crimes
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=crime2
MONGODB_COLLECTION=articles2
OLLAMA_MODEL=llama3.2
```

**Never commit `.env` files.** They are in `.gitignore`.

---

## Docker (Crime Extraction Service)

A `Dockerfile` and `docker-compose.yml` are provided in `crime_extraction_service/`.

```bash
cd crime_extraction_service
docker-compose up --build
```

The `docker-compose.yml` sets up the service with environment variables from `.env`.

---

## Production Build (Frontend)

```bash
cd frontend
npm run build
```

This creates `frontend/build/` — a static site you can serve with:
- Nginx
- Apache
- Any CDN (Netlify, Vercel, S3+CloudFront)

### Nginx Example Config

```nginx
server {
    listen 80;
    root /var/www/frontend/build;
    index index.html;

    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
    }
}
```

---

## Running Backend in Production

```bash
cd backend
source venv/bin/activate

# Production server (no --reload)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

Or use a process manager like `pm2` or `supervisor`:

```bash
# With pm2 (requires pm2 installed)
pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name crime-backend
```

---

## CORS Configuration

The backend currently allows:
```python
allow_origins=["http://localhost:3000", "http://localhost:3001"]
```

For production, update `backend/main.py` to include your actual frontend domain:

```python
allow_origins=["https://your-frontend-domain.com"]
```

---

## MongoDB in Production

Options:
1. **MongoDB Atlas** (cloud) — update `MONGO_URL` in `DBHandler` to your Atlas connection string
2. **Self-hosted** — ensure MongoDB is running and accessible from the backend

To use Atlas:
```python
# In db_handler.py or via env var
MONGO_URL = "mongodb+srv://user:password@cluster.mongodb.net/"
```

---

## What Gets Committed to Git

The `.gitignore` excludes:

```
.env                          # API keys
venv/                         # Python virtual environments
node_modules/                 # Node packages
backend/news_videos/          # Downloaded MP4/MP3 files
*.mp4, *.mp3                  # Media files
backend/extraction_progress.json   # Runtime state
backend/google_news_progress.json  # Runtime state
backend/newsdata_credits.json      # Runtime state
__pycache__/                  # Python bytecode
build/                        # Frontend build output
```

---

## Checklist Before Deploying

- [ ] `.env` files created with real API keys
- [ ] MongoDB running and accessible
- [ ] FFmpeg installed and path configured in `youtube_extractor.py` and `audio_extractor.py`
- [ ] CORS origins updated in `backend/main.py`
- [ ] Frontend `API_BASE_URL` in `frontend/src/services/api.js` points to production backend URL
- [ ] `npm run build` completed for frontend
- [ ] Backend started with `uvicorn` (no `--reload` in production)
