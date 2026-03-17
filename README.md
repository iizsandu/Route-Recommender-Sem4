# Crime-Aware Route Recommendation System

A full-stack web application that combines crime data extraction, route planning, and interactive visualization to help users make informed decisions about their travel routes.

## Features

### 1. Route Map
- Interactive map powered by Leaflet
- Route calculation between origin and destination
- Crime hotspot visualization along routes
- Real-time route planning using OSRM

### 2. Unified Article Extractor
- **Centralized extraction API** - Single source of truth for all article extraction
- **Multiple sources** - Google News + Times of India
- **Indefinite extraction** - Runs in cycles until timeout (default: 2 hours)
- **Auto-save** - Progress saved every 50 articles
- **Smart URL cleaning** - Removes tracking parameters (&ved, &usg, etc.)
- **MongoDB storage** with automatic deduplication
- **Interactive UI** with real-time statistics
- **40+ keywords** across major Indian cities

### 3. YouTube Live News Extractor
- **Live stream extraction** from 6 Indian news channels
- **Audio extraction** using FFmpeg
- **Speech-to-text** using OpenAI Whisper
- **Automatic transcription** and database storage
- **Supported channels**: Aaj Tak, ABP News, India TV, NDTV, Zee News, Republic World

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - NoSQL database for article storage
- **BeautifulSoup4** - Web scraping
- **Requests** - HTTP client
- **Uvicorn** - ASGI server

### Frontend
- **React 18** - UI framework
- **Leaflet** - Interactive maps
- **Axios** - HTTP client
- **CSS3** - Styling

## Project Structure

```
.
├── backend/
│   ├── main.py                      # FastAPI application
│   ├── article_text_extractor.py   # Centralized extraction API
│   ├── unified_extractor.py         # Unified extraction orchestrator
│   ├── article_extractor.py         # Times of India extractor
│   ├── google_news_extractor.py     # Google News extractor
│   ├── youtube_pipeline.py          # YouTube extraction pipeline
│   ├── db_handler.py                # MongoDB operations
│   ├── requirements.txt             # Python dependencies
│   └── venv/                        # Virtual environment
│
├── frontend/
│   ├── src/
│   │   ├── App.js              # Main application
│   │   ├── components/
│   │   │   ├── MapView.js      # Map component
│   │   │   └── ArticleExtractor.js  # Article extractor UI
│   │   └── services/
│   │       └── api.js          # API client
│   ├── public/
│   └── package.json
│
├── SETUP_GUIDE.md              # Detailed setup instructions
└── README.md                   # This file
```

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 22+
- MongoDB (see installation below)
- FFmpeg (for YouTube extraction)
- yt-dlp (for YouTube extraction)

### MongoDB Installation

**Windows:**
1. Download from: https://www.mongodb.com/try/download/community
2. Run installer (choose "Complete")
3. Install as Windows Service
4. Start service: `net start MongoDB`

### Backend Setup

```bash
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs on: **http://localhost:8000**

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs on: **http://localhost:3001**

## Usage

### Unified Article Extraction

1. Navigate to the **"Article Extractor"** tab
2. Click **"Extract Articles"** button
3. System extracts from ALL sources (Google News + Times of India)
4. Runs for 2 hours with auto-save every 50 articles
5. View extracted articles in the grid
6. Click **"Read More"** to view full article

**Features:**
- Extracts from 40+ keywords across major Indian cities
- Auto-saves progress every 50 articles
- Cleans URLs (removes tracking parameters)
- Handles rate limiting gracefully
- Can resume from saved progress

### YouTube Live Extraction

1. Navigate to the **"YouTube Live"** tab
2. Select a news channel (Aaj Tak, ABP News, etc.)
3. Set duration (30-300 seconds)
4. Choose language (Auto-detect, English, or Hindi)
5. Click **"Extract & Transcribe"**
6. Wait 2-5 minutes for processing

**Requirements:**
- FFmpeg installed and in PATH
- yt-dlp installed (`pip install yt-dlp`)
- OpenAI Whisper installed (`pip install openai-whisper`)

### Route Planning

1. Navigate to the **"Route Map"** tab
2. Enter origin (e.g., "Connaught Place, Delhi")
3. Enter destination (e.g., "India Gate, Delhi")
4. Click **"Find Route"**
5. View route and crime hotspots on map

## API Endpoints

### Route Endpoints
- `POST /commute/commute` - Get route and crime hotspots
- `GET /health` - Health check

### Article Endpoints
- `POST /articles/extract-all?timeout_minutes=120` - Unified extraction (ALL methods)
- `POST /articles/extract` - Extract from Times of India only
- `POST /articles/google-news-extract` - Extract from Google News only
- `GET /articles?limit=50&skip=0` - Get stored articles (Times of India)
- `GET /articles2?limit=50&skip=0` - Get stored articles (Google News)
- `GET /articles/stats` - Get article statistics
- `DELETE /articles` - Delete all articles (testing)

### YouTube Endpoints
- `GET /youtube/channels` - Get available channels
- `POST /youtube/extract` - Extract and transcribe live stream

## Features in Detail

### Centralized Article Extraction System

The system uses a centralized extraction API (`article_text_extractor.py`) that:
- Provides single source of truth for all extraction
- Cleans URLs by removing tracking parameters (&ved, &usg, etc.)
- Standardizes data format across all sources
- Handles errors gracefully
- Validates extraction quality

**Extraction Flow:**
```
User clicks "Extract Articles"
    ↓
unified_extractor.py orchestrates
    ↓
Calls google_news_extractor.py + article_extractor.py
    ↓
Both use article_text_extractor.py (centralized API)
    ↓
Articles saved to MongoDB (deduplicated)
    ↓
Statistics returned to frontend
```

**Unified Extraction Features:**
- Runs in cycles until timeout (default: 2 hours)
- No article cap - extracts as many as possible
- Auto-saves every 50 articles to `extraction_progress.json`
- Detects errors and stops after 10 consecutive errors
- Can resume from saved progress

### YouTube Live Extraction Pipeline

Complete pipeline for live news extraction:

1. **Video Extraction** - Downloads live stream using yt-dlp
2. **Audio Extraction** - Converts to MP3 using FFmpeg
3. **Speech-to-Text** - Transcribes using OpenAI Whisper
4. **Database Storage** - Saves transcription to MongoDB

**Supported Models:**
- tiny (39MB) - Fast, lower accuracy
- base (74MB) - Good balance (default)
- small (244MB) - Better accuracy
- medium (769MB) - High accuracy
- large (1.5GB) - Best accuracy

### Article Extraction System

The article extractor:
- Scrapes crime news from Google News RSS and Times of India
- Filters articles by crime-related keywords
- Stores articles in MongoDB with deduplication
- Provides real-time statistics (total, by source)
- Displays articles in a responsive grid layout

**Extracted Data:**
- Title
- URL
- Source
- Published Date
- Description
- Extraction Timestamp

### Route Visualization

The route map:
- Uses public OSRM service for routing
- Geocodes locations using Nominatim
- Displays routes as blue polylines
- Shows crime hotspots as markers
- Interactive popups on crime markers

## Database Schema

**Database:** `crime2`

**Collection: `articles`** (Times of India)
```javascript
{
  title: String,
  url: String (unique),
  source: String,
  published_date: String,
  description: String,
  extracted_at: ISODate
}
```

**Collection: `articles2`** (Google News)
```javascript
{
  url: String (unique),
  title: String,
  date: ISODate,
  text: String,
  summary: String,
  source: String,
  keyword: String,
  extracted_at: String,
  full_text_extracted: Boolean
}
```

**Indexes:**
- `url` (unique) on both collections
- `extracted_at` (descending)

## Development

### Running in Development Mode

Both servers support hot-reload:
- Backend: Uvicorn auto-reloads on file changes
- Frontend: React hot module replacement

### Environment Variables

Backend uses default values:
- MongoDB: `mongodb://localhost:27017/`
- Port: `8000`

Frontend:
- API URL: `http://localhost:8000`
- Port: `3001` (or auto-assigned)

## Troubleshooting

### MongoDB Connection Error
```
✗ MongoDB connection failed
```
**Solution:** Install and start MongoDB service

### Port Already in Use
**Solution:** Stop other processes or let React use another port

### Article Extraction Fails
**Possible causes:**
- No internet connection
- Website blocking scraping
- Rate limiting

**Solution:** System auto-saves progress and can resume

### YouTube Extraction Fails
**Possible causes:**
- FFmpeg not installed or not in PATH
- yt-dlp not installed
- Channel not streaming live
- Network issues

**Solutions:**
- Install FFmpeg: https://www.gyan.dev/ffmpeg/builds/
- Install yt-dlp: `pip install yt-dlp`
- Verify installations: `ffmpeg -version` and `yt-dlp --version`
- Try different channel or shorter duration

## Future Enhancements

- [ ] NER model integration for structured data extraction
- [ ] LLM-based crime event extraction
- [ ] Real crime database integration
- [ ] Advanced filtering and search
- [ ] User authentication
- [ ] Scheduled article extraction
- [ ] Email notifications for new articles
- [ ] Export functionality (CSV, JSON)

## License

This project is for educational purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues and questions:
1. Check SETUP_GUIDE.md
2. Review API documentation
3. Check MongoDB connection
4. Verify all dependencies are installed

---

**Built with ❤️ for safer travel**
