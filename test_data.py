from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def insert_test_data():
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv('MONGODB_URL'))
    db = client[os.getenv('DATABASE_NAME', 'salon_db')]
    
    # Test salon data
    test_salon = {
        "salon_id": "test_salon_1",
        "name": "Beautiful Salon & Spa",
        "address": "123 Main Street, City",
        "phone": "+1234567890",
        "services": [],
        "experts": [],
        "appointments": [],
        "ratings": [],
        "average_rating": 5.0,
        "total_ratings": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    try:
        # Check if salon already exists
        existing = await db.salons.find_one({"salon_id": "test_salon_1"})
        if not existing:
            await db.salons.insert_one(test_salon)
            print("Test salon created successfully!")
        else:
            print("Test salon already exists!")
            
        # Verify salons collection
        count = await db.salons.count_documents({})
        print(f"Total salons in database: {count}")
        
        # List all salons
        async for salon in db.salons.find():
            print(f"Found salon: {salon['name']} (ID: {salon['salon_id']})")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(insert_test_data()) 