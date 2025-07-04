"""
Defines the data models and schemas for the database.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///veritas.db"

# Asynchronous engine for the application
async_engine = create_async_engine(DATABASE_URL, echo=False)

# Synchronous engine for initial table creation (simpler)
sync_engine = create_engine("sqlite:///veritas.db")

# Asynchronous session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

class User(Base):
    """
    Represents a Discord user who has interacted with the bot.
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, unique=True, nullable=False)
    discord_name = Column(String, nullable=False)
    # In a real app, store encrypted credentials here
    # encrypted_twitter_token = Column(Text)

    requests = relationship("InfoRequest", back_populates="user")

class InfoRequest(Base):
    """
    Represents a specific information request made by a user.
    """
    __tablename__ = 'info_requests'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    description = Column(Text, nullable=False)
    keywords = Column(String, nullable=False)
    discord_channel_id = Column(BigInteger, unique=True, nullable=False)
    
    user = relationship("User", back_populates="requests")

def init_db():
    """Creates all database tables."""
    Base.metadata.create_all(bind=sync_engine)