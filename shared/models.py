from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from shared.database import Base

class Task(Base):
    """
    Represents a monitoring task created by a user.
    """
    __tablename__ = 'tasks'
    
    task_id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    telegram_chat_id = Column(BigInteger, nullable=False)
    source_type = Column(String(50), nullable=False)  # e.g., 'reddit', 'rss'
    source_target = Column(Text, nullable=False)  # e.g., 'r/python', URL
    current_prompt = Column(Text, nullable=False)
    status = Column(String(50), default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Task(task_id={self.task_id}, source_type='{self.source_type}', source_target='{self.source_target}')>"
    
    @classmethod
    def get_by_id(cls, session, task_id):
        """Get a task by ID."""
        return session.query(cls).filter(cls.task_id == task_id).first()
    
    @classmethod
    def get_active_tasks(cls, session):
        """Get all active tasks."""
        return session.query(cls).filter(cls.status == 'active').all()
    
    @classmethod
    def get_user_tasks(cls, session, user_id):
        """Get all tasks for a user."""
        return session.query(cls).filter(cls.user_id == user_id).all()
