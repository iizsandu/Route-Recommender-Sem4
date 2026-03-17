# Setup Guide - Crime-Aware Route System

## Prerequisites

### 1. Install MongoDB

**Windows:**
1. Download MongoDB Community Server from: https://www.mongodb.com/try/download/community
2. Run the installer (choose "Complete" installation)
3. Install MongoDB as a Windows Service (recommended)
4. MongoDB will run on `mongodb://localhost:27017/` by default

**Quick Test:**
```bash
mongod --version
```

**Start MongoDB Service (if not running):**
```bash
# Windows
net start MongoDB

# Or manually
mongod --dbpath C:\data\db
```

### 2. Python & Node.js
- Python 3.12+ (already installed ✓)
- Node.js 22+ (already installed ✓)

## Installation Steps

### Backend Setup

1. Navigate to backend folder:
```bash
cd backend
```

2. Activate virtual environment:
```bash
.\venv\Scripts\activate
```

3. Install dependencies (already done):
```bash
pip install -r requirements.txt
```

4. Start the backend server:
```bash
python main.py
```

Backend runs on: http://localhost:8000

### Frontend Setup

1. Navigate to frontend folder:
```bash
cd frontend
```

2. Install dependencies (already done):
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

Frontend runs on: http://localhost:3001

## Features

### 1. Route Map
- Enter origin and destination
- View route on interactive map
- See crime hotspots along the route

### 2. Article Extractor
- Click "Extract Articles" button
- Extracts crime news from:
  - Google News RSS
  - Times of India
- Stores articles in MongoDB
- View extracted articles in grid layout
- Click "Read More" to view full article

## API Endpoints

### Route Endpoints
- `POST /commute/commute` - Get route and crime hotspots
- `GET /health` - Health check

### Article Endpoints
- `POST /articles/extract` - Extract articles from news sources
- `GET /articles` - Get stored articles (limit, skip params)
- `GET /articles/stats` - Get article statistics
- `DELETE /articles` - Delete all articles (testing)

## Troubleshooting

### MongoDB Connection Error
If you see "Failed to connect to MongoDB":
1. Ensure MongoDB is installed
2. Start MongoDB service: `net start MongoDB`
3. Check if MongoDB is running on port 27017

### Port Already in Use
- Backend (8000): Stop other processes using port 8000
- Frontend (3000/3001): React will automatically suggest another port

### Article Extraction Issues
- Requires internet connection
- Some websites may block scraping
- Rate limiting may apply

## Database Structure

**Database:** `crime`

**Collections:**
- `articles` - Extracted news articles
  - Fields: title, url, source, published_date, description, extracted_at

## Next Steps

1. Install MongoDB if not already installed
2. Start both backend and frontend servers
3. Navigate to http://localhost:3001
4. Try the "Article Extractor" tab
5. Click "Extract Articles" to fetch crime news
6. View extracted articles in the grid

## Notes

- Articles are deduplicated by URL
- Extraction takes 5-10 seconds
- Sample crime data is generated for route visualization
- For production, integrate with real crime database
