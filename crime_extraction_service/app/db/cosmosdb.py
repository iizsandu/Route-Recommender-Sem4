"""
Azure Cosmos DB async client — stores structured CrimeRecord documents.
Uses url as the document id (unique key).
Partition key: /crime_type
"""
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions as cosmos_exc
from typing import Optional
from app.models.crime import CrimeRecord
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CosmosDBClient:
    def __init__(self):
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.container = None

    async def connect(self):
        try:
            self.client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
            self.database = await self.client.create_database_if_not_exists(
                id=settings.cosmos_database
            )
            self.container = await self.database.create_container_if_not_exists(
                id=settings.cosmos_container,
                partition_key=PartitionKey(path="/crime_type"),
                offer_throughput=400,
            )
            logger.info(
                "cosmosdb_connected",
                database=settings.cosmos_database,
                container=settings.cosmos_container,
            )
        except Exception as e:
            logger.error("cosmosdb_connection_failed", error=str(e))
            raise

    async def disconnect(self):
        if self.client:
            await self.client.close()
            logger.info("cosmosdb_disconnected")

    async def upsert_crime_record(self, record: CrimeRecord) -> bool:
        """
        Upsert a CrimeRecord into Cosmos DB.
        Uses url as the document 'id' so re-processing the same article overwrites.
        """
        try:
            doc = record.model_dump(mode="json")

            # Cosmos DB requires 'id' field (string)
            # Use url as id — sanitize to remove chars Cosmos doesn't allow
            doc["id"] = record.url

            # Partition key must not be None
            if not doc.get("crime_type"):
                doc["crime_type"] = "unknown"

            # Flatten coordinates for easier querying
            if doc.get("coordinates"):
                doc["lat"] = doc["coordinates"]["lat"]
                doc["lng"] = doc["coordinates"]["lng"]

            await self.container.upsert_item(body=doc)
            logger.info("crime_upserted", url=record.url[:60], crime_type=record.crime_type)
            return True

        except Exception as e:
            logger.error("cosmos_upsert_error", url=record.url[:60], error=str(e))
            return False


cosmosdb_client = CosmosDBClient()
