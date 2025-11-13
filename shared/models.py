"""
Database models for the pipeline system.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from shared.database import Base


class Task(Base):
    """
    Represents a monitoring task created by a user.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    command = Column(String(100), nullable=False)  # e.g., "New Task"
    description = Column(Text, nullable=False)  # Original user request
    source_type = Column(String(50), nullable=False)  # e.g., "reddit", "rss"
    source_params = Column(Text, nullable=False)  # JSON string with scraper params
    current_prompt = Column(Text, nullable=False)  # LLM filtering prompt
    status = Column(String(20), default="active")  # active, paused, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    processed_items = relationship("ProcessedItem", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.id}, user={self.user_email}, status={self.status})>"


class ProcessedItem(Base):
    """
    Tracks items that have been processed for each task to prevent duplicates.
    """
    __tablename__ = "processed_items"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(String(500), nullable=False)  # Unique identifier from source
    processed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="processed_items")

    # Composite index for efficient lookups
    __table_args__ = (
        Index("ix_task_item", "task_id", "item_id", unique=True),
    )

    def __repr__(self):
        return f"<ProcessedItem(task_id={self.task_id}, item_id={self.item_id})>"
