# Setup Guide

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.12+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| MongoDB | 6+ | Article storage |
| FFmpeg | Any | YouTube audio extraction |
| yt-dlp | Latest | YouTube video download |

---

## 1. Clone the Repository

```bash
git clone https://github.com/iizsandu/Route-Recommender-Sem4.git
cd Route-Recommender-Sem4
```

---

## 2. MongoDB Setup

### Windows
1. Download from https://www.mongodb.com/try/download/community
2. Run installer → choose "Complete" → install as Windows Service
3. Start the service:
```bash
net start MongoDB
```

MongoDB will run on `mongodb://localhost:27017/` by default.

The application uses database `crime2` with these collections:
- `articles` — Times of India articles
- `articles2` — Google News + NewsData.io articles
- `youtube` — YouTube transcriptions

---

## 3. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Environment Variables

Create `backend/.env`:

```env
NEWSDATA_API_KEY=your_newsdata_api_key_here
```

Get a free API key at https://newsdata.io/register

### Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs at: http://localhost:8000/docs

---

## 4. Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs at: http://localhost:3000

---

## 5. FFmpeg Setup (for YouTube extraction)

### Windows
1. Download from https://www.gyan.dev/ffmpeg/builds/
2. Extract to a folder, e.g. `D:\ffmpeg\bin`
3. Add to PATH:
   - Open System Properties → Advanced → Environment Variables
   - Under System Variables, find `Path` → Edit → New
   - Add `D:\ffmpeg\bin`
4. Verify: `ffmpeg -version`

The backend also has a hardcoded FFmpeg path fallback in `youtube_extractor.py` and `audio_extractor.py`:
```python
FFMPEG_PATH = r"D:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"
```
Update this path if your FFmpeg is installed elsewhere.

---

## 6. Crime Extraction Service Setup (Optional)

This is a separate microservice for LLM-based crime data extraction.

```bash
cd crime_extraction_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `crime_extraction_service/.env`:

```env
CEREBRAS_API_KEY=your_cerebras_api_key
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key
COSMOS_DATABASE=crime_db
COSMOS_CONTAINER=structured_crimes
MONGODB_URL=mongodb://localhost:27017/
MONGODB_DATABASE=crime2
MONGODB_COLLECTION=articles2
OLLAMA_MODEL=llama3.2
```

Start the service:
```bash
uvicorn app.main:app --reload --port 8001
```

---

## 7. Verify Everything Works

```bash
# Backend health check
curl http://localhost:8000/health

# Article stats
curl http://localhost:8000/articles/stats

# NewsData.io credit status
curl http://localhost:8000/articles/newsdata-credits
```

---

## Common Issues

### MongoDB not connecting
```
MongoDB connection failed: ...
```
Make sure MongoDB service is running: `net start MongoDB`

### FFmpeg not found during YouTube extraction
Update the `FFMPEG_PATH` constant in `backend/youtube_extractor.py` and `backend/audio_extractor.py` to your actual FFmpeg binary path.

### Whisper model download slow
First run downloads the Whisper model (~74MB for `base`). This is normal. Subsequent runs use the cached model.

### NewsData.io 403 error
- Check your API key in `backend/.env`
- Verify the key is activated at https://newsdata.io/dashboard
- Free tier only supports `/latest` endpoint (not `/archive`)
