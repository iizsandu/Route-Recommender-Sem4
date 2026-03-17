"""
Test Cosmos DB Connection and Insert Sample Record
"""
import asyncio
from datetime import datetime
from uuid import uuid4
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE", "crime_db")
COSMOS_CONTAINER = os.getenv("COSMOS_CONTAINER", "structured_crimes")


async def test_cosmos_connection():
    """Test Cosmos DB connection and insert sample record"""
    
    print("=" * 70)
    print("Testing Cosmos DB Connection")
    print("=" * 70)
    print(f"Endpoint: {COSMOS_ENDPOINT}")
    print(f"Database: {COSMOS_DATABASE}")
    print(f"Container: {COSMOS_CONTAINER}")
    print("=" * 70)
    print()
    
    client = None
    
    try:
        # 1. Connect to Cosmos DB
        print("1. Connecting to Cosmos DB...")
        client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
        print("   ✓ Connected successfully")
        print()
        
        # 2. Create database if not exists
        print(f"2. Creating database '{COSMOS_DATABASE}' (if not exists)...")
        database = await client.create_database_if_not_exists(id=COSMOS_DATABASE)
        print(f"   ✓ Database ready")
        print()
        
        # 3. Create container if not exists
        print(f"3. Creating container '{COSMOS_CONTAINER}' (if not exists)...")
        container = await database.create_container_if_not_exists(
            id=COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/crime_type"),
            offer_throughput=1000  # Your RU/s setting
        )
        print(f"   ✓ Container ready")
        print(f"   Partition key: /crime_type")
        print(f"   Throughput: 1000 RU/s")
        print()
        
        # 4. Insert sample crime record
        print("4. Inserting sample crime record...")
        
        sample_crime = {
            "id": str(uuid4()),
            "crime_type": "test_fraud",
            "description": "Sample crime record for testing Cosmos DB connection",
            "location": {
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "address": "Test Address, Connaught Place"
            },
            "date_time": "2024-02-27T10:00:00",
            "victim_count": 1,
            "suspect_count": 1,
            "weapon_used": None,
            "source_article_id": "test_article_123",
            "extraction_confidence": 0.85,
            "created_at": datetime.now().isoformat()
        }
        
        result = await container.create_item(body=sample_crime)
        
        print(f"   ✓ Sample record inserted successfully!")
        print(f"   Record ID: {result['id']}")
        print(f"   Crime Type: {result['crime_type']}")
        print(f"   Location: {result['location']['city']}, {result['location']['state']}")
        print(f"   Confidence: {result['extraction_confidence']}")
        print()
        
        # 5. Query the inserted record
        print("5. Querying inserted record...")
        query = f"SELECT * FROM c WHERE c.id = '{sample_crime['id']}'"
        items = container.query_items(query=query, partition_key=sample_crime['crime_type'])
        
        count = 0
        async for item in items:
            count += 1
            print(f"   ✓ Found record:")
            print(f"     ID: {item['id']}")
            print(f"     Crime Type: {item['crime_type']}")
            print(f"     Description: {item['description']}")
            print(f"     Location: {item['location']['city']}")
        
        if count == 0:
            print("   ✗ Record not found (this shouldn't happen)")
        print()
        
        # 6. Get container statistics
        print("6. Container Statistics...")
        try:
            # Query to count documents
            count_query = "SELECT VALUE COUNT(1) FROM c"
            count_items = container.query_items(query=count_query)
            
            total_count = 0
            async for count_val in count_items:
                total_count = count_val
                break
            
            print(f"   Total documents in container: {total_count}")
        except Exception as e:
            print(f"   Could not get count: {e}")
        print()
        
        # Success summary
        print("=" * 70)
        print("✓ ALL TESTS PASSED!")
        print("=" * 70)
        print()
        print("Your Cosmos DB is ready to use!")
        print()
        print("Next steps:")
        print("1. Start the service: cd crime_extraction_service && start.bat")
        print("2. Process articles: curl -X POST http://localhost:8000/process-batch \\")
        print("                          -H 'Content-Type: application/json' \\")
        print("                          -d '{\"limit\": 10}'")
        print()
        print("View data in Azure Portal:")
        print(f"1. Go to: {COSMOS_ENDPOINT.replace(':443/', '')}")
        print("2. Click 'Data Explorer'")
        print(f"3. Navigate to: {COSMOS_DATABASE} → {COSMOS_CONTAINER} → Items")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("=" * 70)
        print("✗ ERROR")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()
        print("Common issues:")
        print("1. Check COSMOS_ENDPOINT in .env (should start with https://)")
        print("2. Check COSMOS_KEY in .env (long string from Azure Portal)")
        print("3. Verify firewall rules in Azure Portal allow your IP")
        print("4. Ensure you have permissions on the Cosmos DB account")
        print("=" * 70)
        
    finally:
        if client:
            await client.close()
            print("\nConnection closed.")


if __name__ == "__main__":
    asyncio.run(test_cosmos_connection())
