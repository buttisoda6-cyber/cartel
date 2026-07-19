"""SQLite database setup for app data (offers, broadcasts, activity logs).

This uses a separate SQLite database from the read-only SQL Server.
All offers, broadcasts, and activity logs are stored locally in app_data.db.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# SQLite database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "app_data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_app_db() -> Session:
    """Dependency for getting SQLite app database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_app_db():
    """Initialize SQLite database tables."""
    from app_models import Base
    
    Base.metadata.create_all(bind=engine)
