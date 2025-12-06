from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# SQLAlchemy engine (sync)

engine = create_engine(
settings.DATABASE_URL,
pool_pre_ping=True,       # Avoid dropped-connection errors
pool_recycle=3600         # Helps with Railway idle timeouts
)

# Session factory

SessionLocal = sessionmaker(
autocommit=False,
autoflush=False,
bind=engine
)

# Base class for models

Base = declarative_base()

# Dependency for FastAPI endpoints

def get_db():
db = SessionLocal()
try:
yield db
finally:
db.close()
