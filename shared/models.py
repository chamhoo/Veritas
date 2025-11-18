from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from .database import Base
import enum

class TaskStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"

class SourceType(enum.Enum):
    REDDIT = "reddit"
    RSS = "rss"

class Task(Base):
    """Model representing a user's monitoring task."""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False, index=True)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    source_identifier = Column(String(500), nullable=False)  # e.g., subreddit name or RSS URL
    original_request = Column(Text, nullable=False)  # Original user request from email body
    current_prompt = Column(Text, nullable=False)  # LLM prompt for filtering
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Task(id={self.id}, user={self.user_email}, source={self.source_type.value}:{self.source_identifier})>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'source_type': self.source_type.value,
            'source_identifier': self.source_identifier,
            'original_request': self.original_request,
            'current_prompt': self.current_prompt,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProcessedItem(Base):
    """Model to track which items have already been processed for each task."""
    __tablename__ = 'processed_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=False, index=True)
    item_id = Column(String(500), nullable=False)  # Unique identifier for the content item
    processed_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # Ensure we don't process the same item twice for a task
        {'sqlite_autoincrement': True},
    )

    def __repr__(self):
        return f"<ProcessedItem(task_id={self.task_id}, item_id={self.item_id})>"
