import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from app.models import Event
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)


# ------------------------------------------------------
# Helper: Get event by name (uses correct column!)
# ------------------------------------------------------
def get_event_by_name(db: Session, name: str) -> Optional[Event]:
    return (
        db.query(Event)
        .filter(Event.event_name.ilike(name.strip()))
        .first()
    )


# ------------------------------------------------------
# Create event (matches your Event model schema)
# ------------------------------------------------------
def create_event(
    db: Session,
    event_name: str,
    event_date: Optional[str],
    location: Optional[str],
    fight_card: List[Dict[str, Any]],
    raw_metadata: Dict[str, Any]
) -> Event:

    event = Event(
        event_name=event_name,
        event_date=event_date,
        location=location,
        fight_card_json=fight_card,
        metadata_json=raw_metadata,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(f"Created event: {event_name}")
    return event


# ------------------------------------------------------
# Update event (matches Event model’s fields)
# ------------------------------------------------------
def update_event(
    db: Session,
    event: Event,
    event_date: Optional[str],
    location: Optional[str],
    fight_card: Optional[List[Dict[str, Any]]],
    raw_metadata: Optional[Dict[str, Any]]
):
    updated = False

    if event_date is not None:
        event.event_date = event_date
        updated = True

    if location is not None:
        event.location = location
        updated = True

    if fight_card is not None:
        event.fight_card_json = fight_card
        updated = True

    if raw_metadata is not None:
        event.metadata_json = raw_metadata
        updated = True

    if updated:
        db.commit()
        db.refresh(event)
        logger.info(f"Updated event: {event.event_name}")

    return event


# ------------------------------------------------------
# GPT — fetch next UFC event with correct schema
# ------------------------------------------------------
def _gpt_fetch_next_event() -> Optional[Dict[str, Any]]:
    """
    Returns:
    {
      "event_name": "...",
      "event_date": "...",
      "location": "...",
      "fight_card": [
        {"fighter_a": "...", "fighter_b": "..."}
      ]
    }
    """

    prompt = """
    Give me the next upcoming UFC event in pure JSON:

    {
      "event_name": "",
      "event_date": "",
      "location": "",
      "fight_card": [
        {"fighter_a": "", "fighter_b": ""}
      ]
    }

    Only return JSON. No commentary.
    """

    raw = gpt_safe_call([{"role": "user", "content": prompt}])

    import json
    try:
        return json.loads(raw)
    except Exception:
        logger.error("Failed to parse GPT next-event JSON.")
        return None


# ------------------------------------------------------
# MAIN: load_next_event (never returns null)
# ------------------------------------------------------
def load_next_event(db: Session) -> Dict[str, Any]:
    """
    Loads the next UFC event from GPT (safe fallback).
    Saves into DB with correct model fields.
    """

    event_data = _gpt_fetch_next_event()

    if not event_data:
        # ALWAYS return structure
        return {
            "event_name": None,
            "event_date": None,
            "location": None,
            "fight_card": []
        }

    name = event_data["event_name"]
    date = event_data.get("event_date")
    location = event_data.get("location")
    card = event_data["fight_card"]

    existing = get_event_by_name(db, name)

    if existing:
        update_event(
            db,
            event=existing,
            event_date=date,
            location=location,
            fight_card=card,
            raw_metadata=event_data
        )
        return event_data

    create_event(
        db,
        event_name=name,
        event_date=date,
        location=location,
        fight_card=card,
        raw_metadata=event_data
    )

    return event_data
