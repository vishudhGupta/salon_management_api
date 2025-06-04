from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import AsyncGenerator, Optional
import logging
import asyncio
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('database')

# Load environment variables
load_dotenv()

class Database:
    client = None  
    db = None  
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds

    @classmethod
    async def connect_db(cls):
        """Create database connection with retries."""
        retries = 0
        last_error = None

        while retries < cls.MAX_RETRIES:
            try:
                # Get MongoDB URL and database name from environment variables
                mongodb_url = os.getenv('MONGODB_URL')
                database_name = os.getenv('DATABASE_NAME', 'salon_db')

                if not mongodb_url:
                    raise ValueError("MONGODB_URL environment variable is not set")

                logger.info(f"Attempting to connect to MongoDB (Attempt {retries + 1}/{cls.MAX_RETRIES})")
                
                # Create MongoDB client with proper options for Atlas
                cls.client = AsyncIOMotorClient(
                    mongodb_url,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                    maxPoolSize=50,
                    retryWrites=True,
                    retryReads=True
                )
                cls.db = cls.client[database_name]
                
                # Test the connection
                await cls.db.command('ping')
                
                logger.info(f"Successfully connected to MongoDB database: {database_name}")
                
                # Initialize collections if they don't exist
                collections = await cls.db.list_collection_names()
                required_collections = ['users', 'salons', 'experts', 'services', 'appointments', 'ratings', 'notifications', 'expert_availability']
                
                for collection in required_collections:
                    if collection not in collections:
                        await cls.db.create_collection(collection)
                        logger.info(f"Created collection: {collection}")
                
                # If we get here, connection was successful
                return
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                last_error = e
                retries += 1
                if retries < cls.MAX_RETRIES:
                    logger.warning(f"Failed to connect to MongoDB (Attempt {retries}/{cls.MAX_RETRIES}). Retrying in {cls.RETRY_DELAY} seconds...")
                    await asyncio.sleep(cls.RETRY_DELAY)
                continue
            except Exception as e:
                logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
                raise
        
        # If we get here, all retries failed
        logger.error(f"Failed to connect to MongoDB after {cls.MAX_RETRIES} attempts")
        raise last_error

    @classmethod
    async def close_db(cls):
        """Close database connection."""
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("MongoDB connection closed.")

    def __init__(self):
        """Initialize database instance."""
        if self.db is None:
            raise Exception("Database not initialized. Call connect_db() first.")
        
        # Initialize collections
        self.users = self.db.users
        self.salons = self.db.salons
        self.experts = self.db.experts
        self.services = self.db.services
        self.appointments = self.db.appointments
        self.ratings = self.db.ratings
        self.notifications = self.db.notifications
        self.expert_availability = self.db.expert_availability

    @classmethod
    def get_db(cls) -> 'Database':
        """Get database instance."""
        if cls.db is None:
            raise Exception("Database not initialized. Call connect_db() first.")
        return cls()

async def get_db() -> AsyncGenerator[Database, None]:
    """FastAPI dependency for getting database instance."""
    if Database.db is None:
        await Database.connect_db()
    
    db = Database()
    try:
        yield db
    finally:
        pass  # Connection is managed by the class methods 