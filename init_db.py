#!/usr/bin/env python
"""
Database initialization script.
Creates all necessary tables in the database before other services start.
"""
import os
import sys
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Add the parent directory to the path to import shared modules
sys.path.insert(0, '/app')

from shared.database import Base
from shared.models import Task

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def wait_for_db(db_url, max_retries=30, retry_interval=2):
    """Wait for the database to be ready."""
    retries = 0
    while retries < max_retries:
        try:
            engine = create_engine(db_url)
            connection = engine.connect()
            connection.close()
            logger.info("Database is ready!")
            return engine
        except OperationalError as e:
            retries += 1
            logger.warning(f"Database not ready yet (attempt {retries}/{max_retries}): {e}")
            time.sleep(retry_interval)
    
    raise Exception("Could not connect to database after maximum retries")

def init_db():
    """Initialize the database tables."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    logger.info("Waiting for database to be ready...")
    engine = wait_for_db(db_url)
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    
    logger.info("Database initialization complete!")

if __name__ == "__main__":
    init_db()
