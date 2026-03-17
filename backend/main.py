from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from toi_extractor import ArticleExtractor
from db_handler import DBHandler
from youtube_pipeline import YouTubePipeline

app = FastAPI(title="Delhi Crime Data Collector")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
article_extractor = ArticleExtractor()
db_handler = DBHandler()
youtube_pipeline = YouTubePipeline()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── Article Stats ──────────────────────────────────────────────────────────────

@app.get("/articles/stats")
async def get_article_stats():
    try:
        articles_count = db_handler.get_article_count()
        db2 = DBHandler(collection_name="articles2")
        articles2_count = db2.get_article_count()
        return {
            "articles":  {"total": articles_count,  "collection": "articles",  "source": "Times of India"},
            "articles2": {"total": articles2_count, "collection": "articles2", "source": "Google News / NewsData"},
            "total": articles_count + articles2_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles2")
async def get_articles2(limit: int = 50, skip: int = 0):
    try:
        db2 = DBHandler(collection_name="articles2")
        return {"articles": db2.get_articles(limit, skip), "total": db2.get_article_count(), "limit": limit, "skip": skip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Extraction Endpoints ───────────────────────────────────────────────────────

@app.post("/articles/extract-all")
async def extract_all_articles(timeout_minutes: Optional[int] = 120):
    try:
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50)
        result = extractor.extract_indefinitely(timeout_minutes=timeout_minutes)
        return {
            "success": True,
            "message": f"Extraction completed after {result['cycles']} cycles",
            "stats": {
                "cycles": result['cycles'],
                "total_urls": result['total_urls'],
                "total_extracted": result['total_extracted'],
                "elapsed_minutes": round(result['elapsed_minutes'], 1),
                "error_count": result['error_count']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-google-news")
async def extract_google_news_only(timeout_minutes: Optional[int] = 60):
    try:
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50)
        extractor.load_progress()
        keywords = [
            "Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft",
            "Delhi assault", "Delhi rape", "Delhi kidnapping", "Delhi burglary",
            "Delhi police arrest", "Delhi gang", "Delhi violence",
            "New Delhi crime", "NCR crime", "Noida crime", "Gurgaon crime",
        ]
        count = extractor.extract_from_google_news(keywords, pages_per_keyword=20)
        extractor.save_progress()
        return {"success": True, "message": "Google News extraction completed",
                "stats": {"method": "Google News", "new_articles": count, "total_urls": len(extractor.seen_urls)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-times-of-india")
async def extract_times_of_india_only(max_articles: Optional[int] = 200):
    try:
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50)
        extractor.load_progress()
        count = extractor.extract_from_times_of_india(max_articles=max_articles)
        extractor.save_progress()
        return {"success": True, "message": "Times of India extraction completed",
                "stats": {"method": "Times of India", "new_articles": count, "total_urls": len(extractor.seen_urls)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-newsdata")
async def extract_newsdata_only(max_credits: Optional[int] = 200):
    try:
        from unified_extractor import UnifiedExtractor
        from newsdata_credit_manager import credit_manager

        status = credit_manager.get_status()
        if not status['can_use']:
            return {
                "success": False,
                "message": f"No credits available. Reset in {status['hours_until_reset']}h {status['minutes_until_reset']}m",
                "stats": {"method": "NewsData.io", "credits_remaining": 0,
                          "hours_until_reset": status['hours_until_reset'],
                          "minutes_until_reset": status['minutes_until_reset']}
            }

        available = status['credits_remaining']
        if max_credits > available:
            max_credits = available

        extractor = UnifiedExtractor(auto_save_interval=50)
        extractor.load_progress()
        count = extractor.extract_from_newsdata(max_credits=max_credits)
        extractor.save_progress()

        final_status = credit_manager.get_status()
        return {
            "success": True,
            "message": "NewsData.io extraction completed",
            "stats": {
                "method": "NewsData.io", "new_articles": count,
                "total_urls": len(extractor.seen_urls),
                "credits_used": max_credits,
                "credits_remaining": final_status['credits_remaining'],
                "hours_until_reset": final_status['hours_until_reset'],
                "minutes_until_reset": final_status['minutes_until_reset']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles/newsdata-credits")
async def get_newsdata_credits():
    try:
        from newsdata_credit_manager import credit_manager
        return {"success": True, "credits": credit_manager.get_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── YouTube ──

class YouTubeRequest(BaseModel):
    channel: str
    duration: Optional[int] = 60
    language: Optional[str] = None

class YouTubeURLRequest(BaseModel):
    url: str
    language: Optional[str] = None

@app.get("/youtube/channels")
async def get_youtube_channels():
    try:
        return {"channels": youtube_pipeline.get_available_channels()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/youtube/extract")
async def extract_youtube_live(request: YouTubeRequest):
    try:
        result = youtube_pipeline.process_live_stream(
            channel_name=request.channel, duration=request.duration, language=request.language
        )
        if result['success']:
            return {"success": True, "message": f"Processed {request.channel}",
                    "data": {"channel": result['channel'], "video_path": result['video_path'],
                             "audio_path": result['audio_path'],
                             "transcription_length": len(result['transcription']) if result['transcription'] else 0,
                             "saved_to_db": result['saved_to_db']}}
        return {"success": False, "message": result.get('error', 'Unknown error'), "data": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/youtube/extract-url")
async def extract_youtube_url(request: YouTubeURLRequest):
    try:
        result = youtube_pipeline.process_youtube_url(url=request.url, language=request.language)
        if result['success']:
            return {"success": True, "message": "Processed YouTube video",
                    "data": {"url": result['url'], "video_path": result['video_path'],
                             "audio_path": result['audio_path'],
                             "transcription_length": len(result['transcription']) if result['transcription'] else 0,
                             "saved_to_db": result['saved_to_db']}}
        return {"success": False, "message": result.get('error', 'Unknown error'), "data": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
