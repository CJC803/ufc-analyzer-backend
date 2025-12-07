import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Clean up DATABASE_URL – remove whitespace + newlines
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

print("DEBUG DATABASE_URL:", repr(DATABASE_URL))  # Should show NO \n now

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing!")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from app.models import *

# Create tables automatically on startup
Base.metadata.create_all(bind=engine)
