import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

Base = declarative_base()

class Database:
    """
    Database connection and session management.
    """
    def __init__(self, db_url=None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.engine = create_engine(self.db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    def create_tables(self):
        """Create all tables defined in the models."""
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session(self):
        """Get a new session."""
        return self.Session()
