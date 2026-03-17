"""
Azure Cosmos DB async client for storing structured crimes
"""
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from typing import Optional
from app.models.crime import Crime
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CosmosDBClient:
    """Async Cosmos DB client"""
    
    def __init__(self):
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.container = None
    
    async def connect(self):
        """Connect to Cosmos DB and ensure database/container exist"""
        try:
            self.client = CosmosClient(
                settings.cosmos_endpoint,
                credential=settings.cosmos_key
            )
            
            # Create database if not exists
            self.database = await self.client.create_database_if_not_exists(
                id=settings.cosmos_database
            )
            
            # Create container if not exists with partition key
            self.container = await self.database.create_container_if_not_exists(
                id=settings.cosmos_container,
                partition_key=PartitionKey(path="/crime_type"),
                offer_throughput=400
            )
            
            logger.info(
                "cosmosdb_connected",
                database=settings.cosmos_database,
                container=settings.cosmos_container
            )
        except Exception as e:
            logger.error(
                "cosmosdb_connection_failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def disconnect(self):
        """Disconnect from Cosmos DB"""
        if self.client:
            await self.client.close()
            logger.info("cosmosdb_disconnected")
    
    async def insert_crime_record(self, crime: Crime) -> bool:
        """
        Insert a crime record into Cosmos DB
        
        Args:
            crime: Crime object to insert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to dict and ensure proper format
            crime_dict = crime.model_dump(mode='json')
            
            # Ensure crime_type is not None for partition key
            if not crime_dict.get('crime_type'):
                crime_dict['crime_type'] = 'unknown'
            
            # Insert into Cosmos DB
            await self.container.create_item(body=crime_dict)
            
            logger.info(
                "crime_inserted",
                crime_id=crime.id,
                crime_type=crime.crime_type,
                source_article_id=crime.source_article_id,
                confidence=crime.extraction_confidence
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "crime_insert_error",
                crime_id=crime.id,
                source_article_id=crime.source_article_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False


# Global Cosmos DB client instance
cosmosdb_client = CosmosDBClient()
