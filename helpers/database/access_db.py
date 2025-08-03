# (c) @savior_128
import asyncio
import logging
from configs import Config
from helpers.database.database import Database

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def init_db():
    """Initialize database connection and keep it open."""
    try:
        db_instance = Database(Config.MONGODB_URI, Config.DATABASE_NAME)
        await db_instance._client.admin.command("ping")
        logger.info("MongoDB connection initialized")
        return db_instance
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {e}")
        raise

_db_instance = None

async def get_db():
    """Get or initialize the database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = await init_db()
    return _db_instance