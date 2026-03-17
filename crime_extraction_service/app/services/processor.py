"""
Main processing service that orchestrates extraction pipeline
"""
from typing import Dict
from app.services.llm_extractor import LLMExtractor
from app.services.validator import CrimeValidator
from app.db.mongodb import mongodb_client
from app.db.cosmosdb import cosmosdb_client
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CrimeProcessor:
    """Orchestrates the crime extraction pipeline"""
    
    def __init__(self):
        self.extractor = LLMExtractor()
        self.validator = CrimeValidator()
    
    async def process_batch(self, limit: int = 10) -> Dict:
        """
        Process a batch of articles
        
        Args:
            limit: Number of articles to process
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info("batch_processing_started", limit=limit)
        
        stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            # Fetch unprocessed articles
            articles = await mongodb_client.fetch_unprocessed_articles(limit)
            
            if not articles:
                logger.warning("no_articles_found")
                return stats
            
            stats["processed"] = len(articles)
            
            # Process each article
            for article in articles:
                article_id = str(article.get("_id", "unknown"))
                article_text = article.get("text", "")
                
                try:
                    # Extract crime information using LLM
                    extracted_data = await self.extractor.extract_crime_info(article_text)
                    
                    if not extracted_data:
                        logger.warning(
                            "extraction_failed",
                            article_id=article_id
                        )
                        stats["failed"] += 1
                        stats["errors"].append(f"Extraction failed for article {article_id}")
                        continue
                    
                    # Validate extracted data
                    crime = await self.validator.validate_crime(extracted_data, article_id)
                    
                    if not crime:
                        logger.warning(
                            "validation_failed",
                            article_id=article_id
                        )
                        stats["failed"] += 1
                        stats["errors"].append(f"Validation failed for article {article_id}")
                        continue
                    
                    # Store in Cosmos DB
                    success = await cosmosdb_client.insert_crime_record(crime)
                    
                    if success:
                        stats["successful"] += 1
                        # Mark article as processed in MongoDB
                        await mongodb_client.mark_article_processed(article_id)
                    else:
                        stats["failed"] += 1
                        stats["errors"].append(f"Cosmos DB insert failed for article {article_id}")
                    
                except Exception as e:
                    logger.error(
                        "article_processing_error",
                        article_id=article_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    stats["failed"] += 1
                    stats["errors"].append(f"Error processing article {article_id}: {str(e)}")
            
            logger.info(
                "batch_processing_completed",
                processed=stats["processed"],
                successful=stats["successful"],
                failed=stats["failed"]
            )
            
        except Exception as e:
            logger.error(
                "batch_processing_error",
                error=str(e),
                error_type=type(e).__name__
            )
            stats["errors"].append(f"Batch processing error: {str(e)}")
        
        return stats


# Global processor instance
processor = CrimeProcessor()
