import logging
import re
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models import Event
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# ------------------------------------------------------
# Extract JSON from GPT output
# ------------------------------------------------------
def extract_json(text: str) -> str:
    """
    Pulls the FIRST valid JSON object from any text.
    Handles markdown ```json fences, stray characters, etc.
    """

    # 1. Extract JSON inside ```json ... ```
    fenced = re.search(r"```json(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    # 2. Extract ANY {...} JSON block
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return brace.group(0).strip()

    return text.strip()


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
from datetime import datetime

def _gpt_fetch_next_event() -> Optional[Dict[str, Any]]:
    today = datetime.utcnow().strftime("%Y-%m-%d")

    prompt = f"""
    TODAY'S DATE: {today}

    Your task:
    - Return the **next upcoming UFC event AFTER today's date**
    - If you are unsure, pick the best-known *future scheduled* UFC card.
    - Never return any UFC event that occurs BEFORE {today}.

    Respond in PURE JSON ONLY:

    {{
      "event_name": "",
      "event_date": "",   // must be > {today}
      "location": "",
      "fight_card": [
        {{"fighter_a": "", "fighter_b": ""}}
      ]
    }}
    """

    raw = gpt_safe_call([prompt])
    clean = extract_json(raw)

    print("======== RAW GPT EVENT RESPONSE ========")
    print(clean)
    print("========================================")

    try:
        data = json.loads(clean)

        # Auto-reject past events (safety check)
        event_date = data.get("event_date", "")
        if event_date <= today:
            logger.error(f"GPT returned past event: {event_date}")
            return None

        return data

    except Exception as e:
        logger.error(f"Could not parse GPT event response: {e}")
        return None


# ------------------------------------------------------
# Create Event
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
# Update Event
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
# Load Next Event (Main)
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
# Convert ORM → JSON dict
# ------------------------------------------------------
def _event_to_json(event: Event) -> Dict[str, Any]:
    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "location": event.location,
        "fight_card": event.fight_card_json or [],
    }
