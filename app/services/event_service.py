import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models import Event
from app.utils.gpt_safe import gpt_safe_call
import json

logger = logging.getLogger(__name__)


# ------------------------------------------------------
# Get event by name
# ------------------------------------------------------
def get_event_by_name(db: Session, name: str) -> Optional[Event]:
    return (
        db.query(Event)
        .filter(Event.event_name.ilike(name.strip()))
        .first()
    )


# ------------------------------------------------------
# GPT — Fetch Next UFC Event
# ------------------------------------------------------
def _gpt_fetch_next_event() -> Optional[Dict[str, Any]]:
    prompt = """
    Return the *next upcoming UFC event* in PURE JSON only.

    Format EXACTLY:

    {
      "event_name": "",
      "event_date": "",
      "location": "",
      "fight_card": [
        {"fighter_a": "", "fighter_b": ""}
      ]
    }
    """

    raw = gpt_safe_call([prompt])

    print("======== RAW GPT EVENT RESPONSE ========")
    print(raw)
    print("========================================")

    try:
        return json.loads(raw)
    except Exception:
        logger.error("Could not parse GPT event response.")
        return None


# ------------------------------------------------------
# Create event
# ------------------------------------------------------
def create_event(db: Session, data: Dict[str, Any]) -> Event:
    event = Event(
        event_name=data["event_name"],
        event_date=data.get("event_date"),
        location=data.get("location"),
        fight_card_json=data.get("fight_card", []),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(f"Created new event: {event.event_name}")
    return event


# ------------------------------------------------------
# Update event if already exists
# ------------------------------------------------------
def update_event(db: Session, event: Event, data: Dict[str, Any]) -> Event:

    event.event_name = data["event_name"]
    event.event_date = data.get("event_date")
    event.location = data.get("location")
    event.fight_card_json = data.get("fight_card", [])

    db.commit()
    db.refresh(event)

    logger.info(f"Updated event: {event.event_name}")
    return event


# ------------------------------------------------------
# MAIN — Load & save next event
# ------------------------------------------------------
def load_next_event(db: Session) -> Optional[Dict[str, Any]]:
    gpt_data = _gpt_fetch_next_event()
    if not gpt_data:
        return None

    name = gpt_data["event_name"]
    existing = get_event_by_name(db, name)

    if existing:
        updated = update_event(db, existing, gpt_data)
        return _event_to_json(updated)

    new_event = create_event(db, gpt_data)
    return _event_to_json(new_event)


# ------------------------------------------------------
# Convert Event ORM to dict
# ------------------------------------------------------
def _event_to_json(event: Event) -> Dict[str, Any]:
    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "location": event.location,
        "fight_card": event.fight_card_json or [],
    }
