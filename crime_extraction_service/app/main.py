"""
FastAPI application for crime extraction service
"""
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.models.crime import ProcessBatchRequest, ProcessBatchResponse
from app.services.processor import processor
from app.db.mongodb import mongodb_client
from app.db.cosmosdb import cosmosdb_client
from app.utils.logger import configure_logging, get_logger
from app.config import settings

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("service_starting", service=settings.service_name)
    
    try:
        await mongodb_client.connect()
        await cosmosdb_client.connect()
        logger.info("service_started")
    except Exception as e:
        logger.error("service_startup_failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("service_stopping")
    await mongodb_client.disconnect()
    await cosmosdb_client.disconnect()
    logger.info("service_stopped")


# Create FastAPI app
app = FastAPI(
    title="Crime Extraction Service",
    description="Microservice for extracting structured crime information from articles",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "mongodb": {
            "database": settings.mongodb_database,
            "collection": settings.mongodb_collection
        },
        "cosmosdb": {
            "database": settings.cosmos_database,
            "container": settings.cosmos_container
        },
        "llm": {
            "primary": "Cerebras API (llama3.1-8b / gpt-oss-120b)",
            "fallback": f"Ollama ({settings.ollama_model})"
        }
    }


@app.post("/process-batch", response_model=ProcessBatchResponse)
async def process_batch(request: ProcessBatchRequest):
    """
    Process a batch of articles
    
    Fetches N articles from MongoDB, extracts crime information using LLM,
    validates the data, and stores in Cosmos DB.
    
    Args:
        request: ProcessBatchRequest with limit parameter
        
    Returns:
        ProcessBatchResponse with processing statistics
    """
    try:
        logger.info("batch_request_received", limit=request.limit)
        
        # Process the batch
        stats = await processor.process_batch(limit=request.limit)
        
        response = ProcessBatchResponse(
            processed=stats["processed"],
            successful=stats["successful"],
            failed=stats["failed"],
            errors=stats["errors"][:10]  # Limit errors to first 10
        )
        
        logger.info(
            "batch_request_completed",
            processed=response.processed,
            successful=response.successful,
            failed=response.failed
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "batch_request_error",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Batch processing failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process_batch": "/process-batch",
            "docs": "/docs"
        }
    }
