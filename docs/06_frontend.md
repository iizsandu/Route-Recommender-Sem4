# Frontend Documentation

## Tech Stack

- React 18
- Axios for HTTP
- Plain CSS (no UI library)

Runs on: `http://localhost:3000`

---

## Structure

```
frontend/src/
├── App.js                        # Root component, tab navigation
├── App.css                       # Global styles, header, tabs
├── index.js                      # React entry point
├── index.css                     # Body/reset styles
├── components/
│   ├── ArticleExtractor.js       # Article extraction UI
│   ├── ArticleExtractor.css
│   ├── YouTubeExtractor.js       # YouTube extraction UI
│   └── YouTubeExtractor.css
└── services/
    └── api.js                    # All backend API calls
```

---

## `App.js`

Root component with two tabs:

```jsx
const [activeTab, setActiveTab] = useState('articles');

// Renders:
// - ArticleExtractor when activeTab === 'articles'
// - YouTubeExtractor when activeTab === 'youtube'
```

Default tab is `articles`.

---

## `ArticleExtractor.js`

Controls article extraction and displays results.

### State

| State | Type | Purpose |
|-------|------|---------|
| `articles` | Array | Displayed article list |
| `stats` | Object | Article counts per collection |
| `loading` | Boolean | Extraction in progress |
| `extractionMethod` | String | Selected method: `all/google/toi/newsdata` |
| `viewCollection` | String | `articles` or `articles2` |
| `newsDataCredits` | Object | Credit status from backend |
| `error` | String | Error message |
| `successMessage` | String | Success message |

### Extraction Methods Dropdown

```
All Methods (Google News + Times of India + NewsData.io)
Google News Only
Times of India Only
NewsData.io Only (X/200 credits)
```

When `newsdata` is selected, a credit info panel appears showing:
- Credits remaining / max
- Time until reset
- Warning if no credits available

### Collection Viewer

A dropdown lets you switch between viewing `articles2` (Google News) and `articles` (Times of India). Shows live counts from the stats endpoint.

### Article Cards

Each article displays:
- Source badge
- Title
- Description (if available)
- Extraction date
- "Read More →" link to original article

---

## `YouTubeExtractor.js`

Two extraction modes:

### Option 1: Live Channel Extraction

- Select channel from dropdown (populated from `/youtube/channels`)
- Set duration (30–300 seconds)
- Choose language (Auto / English / Hindi)
- Click "Extract Live Stream"

### Option 2: URL Extraction

- Paste any YouTube video URL
- Click "Download & Transcribe Video"

### Processing Indicator

While processing, shows a step-by-step pipeline status:
```
📹 Downloading video from YouTube...
🎵 Extracting audio...
📝 Transcribing speech to text...
💾 Saving to database...
```

### Result Display

After success, shows:
- Channel name or URL
- Video file path
- Audio file path
- Transcription character count
- Whether it was saved to DB

---

## `services/api.js`

All API calls in one file. Base URL: `http://localhost:8000`

### Functions

```javascript
// Extraction
extractArticles(timeoutMinutes)     // POST /articles/extract-all
extractGoogleNews()                 // POST /articles/extract-google-news
extractTimesOfIndia()               // POST /articles/extract-times-of-india
extractNewsData()                   // POST /articles/extract-newsdata

// Data fetching
getArticleStats()                   // GET /articles/stats
getArticles(limit, skip)            // GET /articles
getArticles2(limit, skip)           // GET /articles2
getNewsDataCredits()                // GET /articles/newsdata-credits

// YouTube
getYouTubeChannels()                // GET /youtube/channels
extractYouTubeLive(channel, duration, language)   // POST /youtube/extract
extractYouTubeURL(url, language)    // POST /youtube/extract-url
```

All functions use `axios` and throw `Error` with the backend's `detail` message on failure.

---

## Running the Frontend

```bash
cd frontend
npm install
npm start
```

To build for production:
```bash
npm run build
```

Output goes to `frontend/build/`. Serve with any static file server or configure with your deployment platform.
