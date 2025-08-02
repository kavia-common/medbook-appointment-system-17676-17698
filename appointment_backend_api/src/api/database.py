"""Database session and base configuration."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# PUBLIC_INTERFACE
def get_database_url():
    """Get the database URL from environment variables."""
    # Example: PostgreSQL expected; adapt key as needed for production.
    return os.environ.get("DATABASE_URL", "sqlite:///./app.db")

DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# PUBLIC_INTERFACE
def get_db():
    """Yield a SQLAlchemy session for FastAPI dependencies."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
