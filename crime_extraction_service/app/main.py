"""
FastAPI application — Crime Extraction Service
"""
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.models.crime import ProcessBatchRequest, ProcessBatchResponse
from app.services import processor as proc_module
from app.services.geocoder import get_usage_stats
from app.db.mongodb import mongodb_client
from app.db.cosmosdb import cosmosdb_client
from app.utils.logger import configure_logging, get_logger
from app.config import settings

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("service_starting", service=settings.service_name)
    try:
        await mongodb_client.connect()
        await cosmosdb_client.connect()
        logger.info("service_started")
    except Exception as e:
        logger.error("service_startup_failed", error=str(e))
        raise
    yield
    logger.info("service_stopping")
    await mongodb_client.disconnect()
    await cosmosdb_client.disconnect()
    logger.info("service_stopped")


app = FastAPI(
    title="Crime Extraction Service",
    description="Extracts structured crime data from articles and stores in Cosmos DB",
    version="2.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "mongodb": {"database": settings.mongodb_database, "collection": settings.mongodb_collection},
        "cosmosdb": {"database": settings.cosmos_database, "container": settings.cosmos_container},
        "llm": {"primary": "Cerebras llama3.1-8b → gpt-oss-120b", "fallback": f"Ollama ({settings.ollama_model})"},
        "geocoding": get_usage_stats(),
    }


@app.post("/process-batch", response_model=ProcessBatchResponse)
async def process_batch(request: ProcessBatchRequest):
    """
    Process up to `limit` unprocessed articles.
    Set reprocess=true to reprocess already-processed articles.
    """
    try:
        stats = await proc_module.process_batch(limit=request.limit, reprocess=request.reprocess)
        return ProcessBatchResponse(**stats)
    except Exception as e:
        logger.error("process_batch_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-all", response_model=ProcessBatchResponse)
async def process_all():
    """
    Reprocess ALL articles in the collection (ignores processed flag).
    Useful for full re-extraction with new schema.
    """
    try:
        stats = await proc_module.process_batch(limit=100_000, reprocess=True)
        return ProcessBatchResponse(**stats)
    except Exception as e:
        logger.error("process_all_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "process_batch": "POST /process-batch",
            "process_all": "POST /process-all",
            "docs": "/docs",
        },
    }
