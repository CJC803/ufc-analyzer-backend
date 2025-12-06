import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import Event
from app.utils.event_lookup import get_next_ufc_event

logger = logging.getLogger(**name**)

# ---------------------------------------------------------

# Helper: Get or create event by name

# ---------------------------------------------------------

def _get_or_create_event(db: Session, event_name: str) -> Event:
event = (
db.query(Event)
.filter(Event.event_name.ilike(event_name))
.first()
)

```
if event:
    return event

event = Event(event_name=event_name)
db.add(event)
db.commit()
db.refresh(event)
return event
```

# ---------------------------------------------------------

# Public: Load next UFC event (scrape + cache)

# ---------------------------------------------------------

def load_next_event(db: Session) -> Dict[str, Any]:
"""
Runs the event lookup pipeline (UFCStats → fallback GPT)
Then caches the event JSON if new or updated.
"""

```
logger.info("Loading next UFC event via event_lookup pipeline...")

event_json = get_next_ufc_event()

event_name = event_json.get("event_name")
if not event_name:
    raise RuntimeError("Event lookup returned no event_name.")

event = _get_or_create_event(db, event_name)

# Update key fields (C strategy: store JSON only for now)
event.event_date = event_json.get("event_date")
event.location = event_json.get("location")
event.fight_card = event_json.get("fight_card")  # raw JSON

db.commit()

return event_json
```

# ---------------------------------------------------------

# Public: Get latest cached event

# ---------------------------------------------------------

def get_latest_event(db: Session) -> Optional[Dict[str, Any]]:
event = (
db.query(Event)
.order_by(Event.id.desc())
.first()
)

```
if not event:
    return None

return {
    "event_name": event.event_name,
    "event_date": event.event_date,
    "location": event.location,
    "fight_card": event.fight_card,
}
```

# ---------------------------------------------------------

# Public: Get event by name

# ---------------------------------------------------------

def get_event_by_name(db: Session, name: str) -> Optional[Dict[str, Any]]:
event = (
db.query(Event)
.filter(Event.event_name.ilike(name))
.first()
)

```
if not event:
    return None

return {
    "event_name": event.event_name,
    "event_date": event.event_date,
    "location": event.location,
    "fight_card": event.fight_card,
}
```
