"""
Handles all database connections and operations (e.g., storing user credentials securely, tracking requests).
"""

from contextlib import asynccontextmanager
from src.data.models import AsyncSessionLocal, User, InfoRequest
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_session():
    """Provide a transactional scope around a series of operations."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error occurred: {e}")
        raise
    finally:
        await session.close()

async def get_or_create_user(discord_id: int, discord_name: str):
    """
    Retrieves a user by their Discord ID or creates a new one.
    """
    async with get_session() as session:
        result = await session.execute(select(User).filter(User.discord_id == discord_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(discord_id=discord_id, discord_name=discord_name)
            session.add(user)
            await session.flush() # Flushes to get the ID without committing
            logger.info(f"Created new user: {discord_name} (ID: {discord_id})")
        return user

async def create_info_request(user_id: int, description: str, keywords: str, channel_id: int):
    """
    Creates and stores a new information request.
    """
    async with get_session() as session:
        new_request = InfoRequest(
            user_id=user_id,
            description=description,
            keywords=keywords,
            discord_channel_id=channel_id
        )
        session.add(new_request)
        await session.flush()
        logger.info(f"Created new info request for user ID {user_id} in channel {channel_id}")
        return new_request

async def get_all_active_requests():
    """
    Retrieves all active information requests from the database.
    """
    async with get_session() as session:
        result = await session.execute(select(InfoRequest))
        return result.scalars().all()

async def get_request_by_channel_id(channel_id: int):
    """
    Finds an information request based on its dedicated Discord channel ID.
    """
    async with get_session() as session:
        result = await session.execute(
            select(InfoRequest).filter(InfoRequest.discord_channel_id == channel_id)
        )
        return result.scalar_one_or_none()