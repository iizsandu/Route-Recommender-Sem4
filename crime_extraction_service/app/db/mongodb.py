"""
MongoDB async client for reading raw articles
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBClient:
    """Async MongoDB client"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_database]
            self.collection = self.db[settings.mongodb_collection]
            
            # Test connection
            await self.client.admin.command('ping')
            
            logger.info(
                "mongodb_connected",
                database=settings.mongodb_database,
                collection=settings.mongodb_collection
            )
        except Exception as e:
            logger.error(
                "mongodb_connection_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("mongodb_disconnected")
    
    async def fetch_unprocessed_articles(self, limit: int = 10) -> List[Dict]:
        """
        Fetch unprocessed articles from MongoDB
        
        Args:
            limit: Maximum number of articles to fetch
            
        Returns:
            List of article documents
        """
        try:
            # Query for articles with text content
            # You can add a 'processed' flag to track which articles have been processed
            query = {
                "text": {"$exists": True, "$ne": "", "$ne": None}
            }
            
            cursor = self.collection.find(query).limit(limit)
            articles = await cursor.to_list(length=limit)
            
            logger.info(
                "articles_fetched",
                count=len(articles),
                limit=limit
            )
            
            return articles
            
        except Exception as e:
            logger.error(
                "fetch_articles_error",
                error=str(e),
                error_type=type(e).__name__
            )
            return []
    
    async def mark_article_processed(self, article_id: str):
        """
        Mark an article as processed
        
        Args:
            article_id: The article ID to mark
        """
        try:
            await self.collection.update_one(
                {"_id": article_id},
                {"$set": {"processed": True, "processed_at": None}}
            )
            logger.info("article_marked_processed", article_id=str(article_id))
        except Exception as e:
            logger.error(
                "mark_processed_error",
                article_id=str(article_id),
                error=str(e)
            )


# Global MongoDB client instance
mongodb_client = MongoDBClient()
