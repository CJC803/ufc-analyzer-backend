import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from app.models import Event
from app.services.analysis_service import analyze_matchup
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)


# ------------------------------------------------------
# Get event by name
# ------------------------------------------------------
def get_event_by_name(db: Session, name: str) -> Optional[Event]:
    return (
        db.query(Event)
        .filter(Event.name.ilike(name.strip()))
        .first()
    )


# ------------------------------------------------------
# Create event record
# ------------------------------------------------------
def create_event(
    db: Session,
    name: str,
    fights: List[Dict[str, Any]],
    raw_metadata: Dict[str, Any] = None
) -> Event:

    event = Event(
        name=name,
        fights=fights,
        metadata_json=raw_metadata or {},
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info(f"Created event: {name}")

    return event


# ------------------------------------------------------
# Update event
# ------------------------------------------------------
def update_event(
    db: Session,
    event: Event,
    fights: Optional[List[Dict[str, Any]]] = None,
    raw_metadata: Optional[Dict[str, Any]] = None
):
    updated = False

    if fights is not None:
        event.fights = fights
        updated = True

    if raw_metadata is not None:
        event.metadata_json = raw_metadata
        updated = True

    if updated:
        db.commit()
        db.refresh(event)
        logger.info(f"Updated event: {event.name}")

    return event


# ------------------------------------------------------
# GPT — fetch next UFC event + card
# ------------------------------------------------------
def _gpt_fetch_next_event() -> Optional[Dict[str, Any]]:
    prompt = """
    Give me the next upcoming UFC event.
    Return structured JSON with:

    {
      "event_name": "...",
      "date": "...",
      "card": [
        {"fighter1": "...", "fighter2": "..."}
      ]
    }

    Only JSON. No commentary.
    """

    raw = gpt_safe_call([{"role": "user", "content": prompt}])

    try:
        import json
        return json.loads(raw)
    except Exception:
        logger.error("Could not parse GPT event response.")
        return None


# ------------------------------------------------------
# MAIN: Load the next event
# ------------------------------------------------------
def load_next_event(db: Session) -> Optional[Event]:
    """
    Queries GPT for the next event & matchups.
    Saves or updates an Event entry.
    """

    event_data = _gpt_fetch_next_event()
    if not event_data:
        return None

    name = event_data["event_name"]
    card = event_data["card"]

    existing = get_event_by_name(db, name)

    if existing:
        return update_event(db, existing, fights=card, raw_metadata=event_data)

    return create_event(db, name=name, fights=card, raw_metadata=event_data)
