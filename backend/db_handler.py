from pymongo import MongoClient, ASCENDING
from datetime import datetime
from typing import List, Dict, Optional

class DBHandler:
    def __init__(self, mongo_url: str = "mongodb://localhost:27017/", collection_name: str = "articles"):
        self.connected = False
        self.client = None
        self.db = None
        self.articles_collection = None
        self.collection_name = collection_name
        
        try:
            self.client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            self.client.server_info()
            self.db = self.client["crime2"]
            self.articles_collection = self.db[collection_name]
            self._create_indexes()
            self.connected = True
            print(f" Connected to crime2.{collection_name}")
        except Exception as e:
            print(f" MongoDB connection failed: {e}")
    
    def _create_indexes(self):
        try:
            existing = self.articles_collection.index_information()
            # Drop url_1 if it exists (handles spec conflicts or duplicate data blocking rebuild)
            if 'url_1' in existing:
                try:
                    self.articles_collection.drop_index('url_1')
                except Exception:
                    pass
            # Remove duplicate URLs before creating unique index
            pipeline = [
                {"$group": {"_id": "$url", "ids": {"$push": "$_id"}, "count": {"$sum": 1}}},
                {"$match": {"count": {"$gt": 1}}}
            ]
            for doc in self.articles_collection.aggregate(pipeline):
                # Keep the first, delete the rest
                ids_to_delete = doc["ids"][1:]
                self.articles_collection.delete_many({"_id": {"$in": ids_to_delete}})
            self.articles_collection.create_index([("url", ASCENDING)], unique=True, sparse=True, name="url_1")
            self.articles_collection.create_index([("extracted_at", ASCENDING)])
        except Exception as e:
            print(f"  Index creation note: {e}")
    
    def save_articles(self, articles: List[Dict]) -> Dict:
        if not self.connected:
            raise Exception("MongoDB not connected")
        
        inserted_count = 0
        duplicate_count = 0
        errors = []
        
        for article in articles:
            try:
                self.articles_collection.insert_one(article)
                inserted_count += 1
            except Exception as e:
                if "duplicate key error" in str(e).lower():
                    duplicate_count += 1
                else:
                    errors.append(str(e))
        
        return {
            "inserted": inserted_count,
            "duplicates": duplicate_count,
            "errors": len(errors),
            "total_processed": len(articles)
        }
    
    def get_articles(self, limit: int = 50, skip: int = 0) -> List[Dict]:
        if not self.connected:
            return []
        
        articles = list(
            self.articles_collection
            .find({}, {"_id": 0})
            .sort("extracted_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return articles
    
    def get_article_count(self) -> int:
        if not self.connected:
            return 0
        return self.articles_collection.count_documents({})
    
    

    
