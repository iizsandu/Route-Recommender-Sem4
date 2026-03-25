from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import threading
from toi_extractor import ArticleExtractor
from db_handler import DBHandler
from youtube_pipeline import YouTubePipeline

app = FastAPI(title="Delhi Crime Data Collector")

# Global cancel event — set this to stop any running extraction
_cancel_event = threading.Event()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
article_extractor = ArticleExtractor()
db_handler = DBHandler(skip_indexes=True)
youtube_pipeline = YouTubePipeline()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ── Article Stats ──────────────────────────────────────────────────────────────

@app.get("/articles/stats")
async def get_article_stats():
    try:
        import re
        db = DBHandler(collection_name="articles2", skip_indexes=True)
        if not db.connected:
            raise Exception("MongoDB not connected")
        col = db.articles_collection

        total = col.count_documents({})
        breakdown = {
            "Google News":     col.count_documents({"source": "Google News"}),
            "Times of India":  col.count_documents({"source": "Times of India"}),
            "The Hindu":       col.count_documents({"source": "The Hindu"}),
            "NDTV":            col.count_documents({"source": "NDTV"}),
            "Indian Express":  col.count_documents({"source": "Indian Express"}),
            "NewsData.io":     col.count_documents({"source": re.compile(r"^NewsData\.io")}),
            "NewsAPI.org":     col.count_documents({"source": "NewsAPI.org"}),
        }

        return {"total": total, "breakdown": breakdown}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles2")
async def get_articles2(limit: int = 50, skip: int = 0):
    try:
        db2 = DBHandler(collection_name="articles2", skip_indexes=True)
        return {"articles": db2.get_articles(limit, skip), "total": db2.get_article_count(), "limit": limit, "skip": skip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Extraction Endpoints ───────────────────────────────────────────────────────

@app.post("/articles/cancel-extraction")
async def cancel_extraction():
    _cancel_event.set()
    return {"success": True, "message": "Cancellation signal sent. Extraction will stop and save progress shortly."}


@app.post("/articles/extract-all")
async def extract_all_articles(timeout_minutes: Optional[int] = 120):
    try:
        _cancel_event.clear()
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        result = extractor.extract_indefinitely(timeout_minutes=timeout_minutes)
        return {
            "success": True,
            "message": f"Extraction completed after {result['cycles']} cycles",
            "stats": {
                "cycles": result['cycles'],
                "total_urls": result['total_urls'],
                "total_extracted": result['total_extracted'],
                "elapsed_minutes": round(result['elapsed_minutes'], 1),
                "error_count": result['error_count'],
                "source_breakdown": result['source_breakdown'],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-google-news")
async def extract_google_news_only(timeout_minutes: Optional[int] = 60):
    try:
        _cancel_event.clear()
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        keywords = [
            "Delhi crime", "Delhi murder", "Delhi robbery", "Delhi theft",
            "Delhi assault", "Delhi rape", "Delhi kidnapping", "Delhi burglary",
            "Delhi police arrest", "Delhi gang", "Delhi violence",
            "New Delhi crime", "NCR crime", "Noida crime", "Gurgaon crime",
        ]
        count = extractor.extract_from_google_news(keywords)
        extractor.save_progress()
        extractor._print_summary()
        return {"success": True, "message": "Google News extraction completed",
                "stats": {"method": "Google News", "new_articles": count,
                          "total_urls": len(extractor.seen_urls),
                          "source_breakdown": extractor.source_counts}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-times-of-india")
async def extract_times_of_india_only():
    try:
        _cancel_event.clear()
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        count = extractor.extract_from_times_of_india()
        extractor.save_progress()
        extractor._print_summary()
        return {"success": True, "message": "Times of India extraction completed",
                "stats": {"method": "Times of India", "new_articles": count,
                          "total_urls": len(extractor.seen_urls),
                          "source_breakdown": extractor.source_counts}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-hindu")
async def extract_hindu_only():
    try:
        _cancel_event.clear()
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        count = extractor.extract_from_hindu()
        extractor.save_progress()
        extractor._print_summary()
        return {"success": True, "message": "The Hindu extraction completed",
                "stats": {"method": "The Hindu", "new_articles": count,
                          "total_urls": len(extractor.seen_urls),
                          "source_breakdown": extractor.source_counts}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-ndtv")
async def extract_ndtv_only():
    try:
        _cancel_event.clear()
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        count = extractor.extract_from_ndtv()
        extractor.save_progress()
        extractor._print_summary()
        return {"success": True, "message": "NDTV extraction completed",
                "stats": {"method": "NDTV", "new_articles": count,
                          "total_urls": len(extractor.seen_urls),
                          "source_breakdown": extractor.source_counts}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-indian-express")
async def extract_indian_express_only():
    try:
        _cancel_event.clear()
        from unified_extractor import UnifiedExtractor
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        count = extractor.extract_from_indian_express()
        extractor.save_progress()
        extractor._print_summary()
        return {"success": True, "message": "Indian Express extraction completed",
                "stats": {"method": "Indian Express", "new_articles": count,
                          "total_urls": len(extractor.seen_urls),
                          "source_breakdown": extractor.source_counts}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-newsdata")
async def extract_newsdata_only(max_credits: Optional[int] = 200):
    try:
        from unified_extractor import UnifiedExtractor
        from newsdata_credit_manager import credit_manager

        status = credit_manager.get_status()
        if status['credits_remaining'] <= 0:
            return {
                "success": False,
                "message": f"No daily credits left. Reset in {status['hours_until_reset']}h {status['minutes_until_reset']}m",
                "stats": {
                    "method": "NewsData.io",
                    "credits_remaining": 0,
                    "hours_until_reset": status['hours_until_reset'],
                    "minutes_until_reset": status['minutes_until_reset'],
                    "window_remaining": status['window_remaining'],
                    "window_wait_seconds": status['window_wait_seconds'],
                }
            }

        available = status['credits_remaining']
        if max_credits > available:
            max_credits = available

        _cancel_event.clear()
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        count = extractor.extract_from_newsdata(max_credits=max_credits)
        extractor.save_progress()

        final_status = credit_manager.get_status()
        extractor._print_summary()
        return {
            "success": True,
            "message": "NewsData.io extraction completed",
            "stats": {
                "method": "NewsData.io",
                "new_articles": count,
                "total_urls": len(extractor.seen_urls),
                "credits_used": max_credits,
                "credits_remaining": final_status['credits_remaining'],
                "hours_until_reset": final_status['hours_until_reset'],
                "minutes_until_reset": final_status['minutes_until_reset'],
                "window_remaining": final_status['window_remaining'],
                "window_wait_seconds": final_status['window_wait_seconds'],
                "source_breakdown": extractor.source_counts,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles/newsdata-credits")
async def get_newsdata_credits():
    try:
        from newsdata_credit_manager import credit_manager
        status = credit_manager.get_status()
        return {"success": True, "credits": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/articles/extract-newsapi")
async def extract_newsapi_only(max_requests: Optional[int] = 100):
    try:
        from unified_extractor import UnifiedExtractor
        from newsapi_request_manager import newsapi_request_manager

        status = newsapi_request_manager.get_status()
        if not status['can_use']:
            return {
                "success": False,
                "message": f"No daily requests left. Reset in {status['hours_until_reset']}h {status['minutes_until_reset']}m",
                "stats": {
                    "method": "NewsAPI.org",
                    "requests_remaining": 0,
                    "hours_until_reset": status['hours_until_reset'],
                    "minutes_until_reset": status['minutes_until_reset'],
                }
            }

        available = status['requests_remaining']
        if max_requests > available:
            max_requests = available

        _cancel_event.clear()
        extractor = UnifiedExtractor(auto_save_interval=50, cancel_event=_cancel_event)
        extractor.load_progress()
        count = extractor.extract_from_newsapi(max_requests=max_requests)
        extractor.save_progress()

        final_status = newsapi_request_manager.get_status()
        extractor._print_summary()
        return {
            "success": True,
            "message": "NewsAPI.org extraction completed",
            "stats": {
                "method": "NewsAPI.org",
                "new_articles": count,
                "total_urls": len(extractor.seen_urls),
                "requests_used": max_requests,
                "requests_remaining": final_status['requests_remaining'],
                "hours_until_reset": final_status['hours_until_reset'],
                "minutes_until_reset": final_status['minutes_until_reset'],
                "source_breakdown": extractor.source_counts,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/articles/newsapi-requests")
async def get_newsapi_requests():
    try:
        from newsapi_request_manager import newsapi_request_manager
        status = newsapi_request_manager.get_status()
        return {"success": True, "requests": status}
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
