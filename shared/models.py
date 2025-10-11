from sqlalchemy import Column, Integer, String, Text
from .database import Base

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)
    source_target = Column(Text, nullable=False)
    current_prompt = Column(Text, nullable=False)
    status = Column(String(50), default='active')

    def __repr__(self):
        return f"<Task(id={self.task_id}, email={self.user_email}, source={self.source_type}:{self.source_target}, status={self.status})>"
