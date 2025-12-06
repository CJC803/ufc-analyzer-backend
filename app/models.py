from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey

from app.database import Base


# ---------------------------------------------------------
# Fighter Model
# ---------------------------------------------------------

class Fighter(Base):
    __tablename__ = "fighters"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, unique=True)

    # External identifiers
    ufcstats_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sherdog_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tapology_slug: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Cached fighter data (JSON blobs)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    sherdog_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ufcstats_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    tapology_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# ---------------------------------------------------------
# Event Model
# ---------------------------------------------------------

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_name: Mapped[str] = mapped_column(String, index=True)
    event_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Full fight card stored as JSON
    fight_card_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------
# Prediction Model
# ---------------------------------------------------------

class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    event = relationship("Event")

    # GPT output stored raw
    analysis_json: Mapped[Dict[str, Any]] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
