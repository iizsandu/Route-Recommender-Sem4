# Quick Start Guide

## Current Status ✓

✅ Backend running on: **http://localhost:8000**
✅ Frontend running on: **http://localhost:3001**

## Access the Application

Open your browser and go to:
```
http://localhost:3001
```

## Using the Article Extractor

1. Click the **"Article Extractor"** tab at the top
2. Click the green **"Extract Articles"** button
3. Wait 5-10 seconds while articles are being extracted
4. View the extracted articles in the grid below
5. Click **"Read More"** on any article to view the full story

## Using the Route Map

1. Click the **"Route Map"** tab at the top
2. Enter an origin location (e.g., "Connaught Place, Delhi")
3. Enter a destination location (e.g., "India Gate, Delhi")
4. Click **"Find Route"**
5. View the route (blue line) and crime markers on the map

## MongoDB Setup (Optional but Recommended)

Without MongoDB, articles won't be saved between sessions.

### Install MongoDB on Windows:

1. Download: https://www.mongodb.com/try/download/community
2. Run the installer
3. Choose "Complete" installation
4. Install as Windows Service
5. Start the service:
   ```bash
   net start MongoDB
   ```

### Verify MongoDB is Running:

```bash
mongod --version
```

Once MongoDB is running, restart the backend:
```bash
# Stop current backend (Ctrl+C in terminal)
cd backend
.\venv\Scripts\activate
python main.py
```

You should see: `✓ MongoDB connected successfully`

## Testing Without MongoDB

You can test article extraction without MongoDB:

```bash
cd backend
.\venv\Scripts\activate
python test_extractor.py
```

This will extract articles and display them in the console.

## Stopping the Servers

### Stop Backend:
- Press `Ctrl+C` in the backend terminal

### Stop Frontend:
- Press `Ctrl+C` in the frontend terminal

## Restarting the Servers

### Backend:
```bash
cd backend
.\venv\Scripts\activate
python main.py
```

### Frontend:
```bash
cd frontend
npm start
```

## Troubleshooting

### "MongoDB connection failed"
- Install MongoDB (see above)
- Start MongoDB service: `net start MongoDB`
- Articles will still extract but won't be saved

### "Port already in use"
- Stop other applications using ports 8000 or 3000/3001
- Or let React use a different port (it will ask)

### "Failed to extract articles"
- Check your internet connection
- Try again (some sites may temporarily block requests)

### Frontend not loading
- Check if backend is running on port 8000
- Check browser console for errors
- Try refreshing the page

## API Endpoints

Test the API directly:

```bash
# Health check
curl http://localhost:8000/health

# Extract articles
curl -X POST http://localhost:8000/articles/extract

# Get articles
curl http://localhost:8000/articles

# Get statistics
curl http://localhost:8000/articles/stats
```

## Features

### Article Extractor
- Extracts from Google News and Times of India
- Filters for crime-related articles
- Shows statistics (total articles, by source)
- Displays articles in a grid
- Links to original articles

### Route Map
- Interactive map with zoom and pan
- Route visualization (blue line)
- Crime hotspot markers (red pins)
- Click markers to see "Crime Zone" popup

## File Structure

```
.
├── backend/
│   ├── main.py              # API server
│   ├── article_extractor.py # Extraction logic
│   ├── db_handler.py        # Database operations
│   └── venv/                # Virtual environment
│
├── frontend/
│   ├── src/
│   │   ├── App.js           # Main application
│   │   └── components/      # React components
│   └── node_modules/        # Dependencies
│
└── Documentation files
```

## Need Help?

1. Check **SETUP_GUIDE.md** for detailed setup
2. Check **README.md** for full documentation
3. Check **PROJECT_SUMMARY.md** for technical details
4. Check backend terminal for error messages
5. Check browser console for frontend errors

---

**Ready to use!** Open http://localhost:3001 and start extracting articles.
