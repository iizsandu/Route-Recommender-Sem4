"""
MongoDB async client — reads raw articles from articles2 collection.
"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Dict, Optional
from datetime import datetime
from bson import ObjectId
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBClient:
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.collection = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_database]
            self.collection = self.db[settings.mongodb_collection]
            await self.client.admin.command("ping")
            logger.info(
                "mongodb_connected",
                database=settings.mongodb_database,
                collection=settings.mongodb_collection,
            )
        except Exception as e:
            logger.error("mongodb_connection_failed", error=str(e))
            raise

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("mongodb_disconnected")

    async def fetch_unprocessed_articles(
        self, limit: int = 10, reprocess: bool = False
    ) -> List[Dict]:
        """
        Fetch articles that have full text and haven't been processed yet.
        If reprocess=True, fetch all articles regardless of processed flag.
        """
        try:
            has_text = {"$or": [
                {"full_text": {"$exists": True, "$ne": "", "$ne": None}},
                {"text": {"$exists": True, "$ne": "", "$ne": None}},
            ]}
            not_processed = {"$or": [
                {"processed": {"$exists": False}},
                {"processed": {"$ne": True}},
            ]}

            if reprocess:
                query = {"full_text_extracted": True, **has_text}
            else:
                query = {
                    "full_text_extracted": True,
                    "$and": [has_text, not_processed],
                }

            cursor = self.collection.find(query).limit(limit)
            articles = await cursor.to_list(length=limit)
            logger.info("articles_fetched", count=len(articles), reprocess=reprocess)
            return articles
        except Exception as e:
            logger.error("fetch_articles_error", error=str(e))
            return []

    async def mark_article_processed(self, article_id: str):
        try:
            oid = ObjectId(article_id) if ObjectId.is_valid(article_id) else article_id
            await self.collection.update_one(
                {"_id": oid},
                {"$set": {"processed": True, "processed_at": datetime.utcnow()}},
            )
            logger.info("article_marked_processed", article_id=article_id)
        except Exception as e:
            logger.error("mark_processed_error", article_id=article_id, error=str(e))


mongodb_client = MongoDBClient()
