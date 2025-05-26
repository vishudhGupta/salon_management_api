from config.database import Database
from passlib.context import CryptContext
from pydantic import SecretStr
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def migrate_passwords():
    try:
        db = Database()
        users = await db.users.find().to_list(length=None)
        
        for user in users:
            try:
                # Get the password value, handling both string and SecretStr cases
                password = user["password"]
                if isinstance(password, SecretStr):
                    password = password.get_secret_value()
                
                # Skip if password is already hashed
                if isinstance(password, str) and password.startswith("$2b$"):
                    logger.info(f"Password already hashed for user: {user.get('email', 'Unknown')}")
                    continue
                    
                # Hash the password
                hashed_password = pwd_context.hash(password)
                
                # Update the user document
                await db.users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"password": hashed_password}}
                )
                logger.info(f"Successfully migrated password for user: {user.get('email', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error migrating password for user {user.get('email', 'Unknown')}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    finally:
        await db.close()

if __name__ == "__main__":
    try:
        asyncio.run(migrate_passwords())
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}") 