from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

# -------------------------

# Fighter Model

# -------------------------

class Fighter(Base):
**tablename** = "fighters"

```
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
updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

# -------------------------

# Event Model

# -------------------------

class Event(Base):
**tablename** = "events"

```
id: Mapped[int] = mapped_column(primary_key=True, index=True)

event_name: Mapped[str] = mapped_column(String, index=True)
event_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
location: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# Raw fight card JSON (fighter names, order, weight class)
fight_card_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

# -------------------------

# Prediction Model

# -------------------------

class Prediction(Base):
**tablename** = "predictions"

```
id: Mapped[int] = mapped_column(primary_key=True, index=True)

event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
event = relationship("Event")

# Store the full GPT analysis output (raw + parsed)
analysis_json: Mapped[Dict[str, Any]] = mapped_column(JSON)

created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```
