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
import requests
from datetime import datetime
from app.config import settings

ODDS_API_KEY = settings.THE_ODDS_API_KEY   # or ODDS_API_KEY if renamed
EVENTS_ENDPOINT = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/events"


def _fetch_next_event_from_odds_api() -> Optional[Dict[str, Any]]:
    """
    Uses The Odds API to fetch REAL upcoming MMA events.
    Returns the NEXT event in your standardized structure.
    """

    params = {
        "apiKey": ODDS_API_KEY,
    }

    try:
        resp = requests.get(EVENTS_ENDPOINT, params=params, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Odds API event request failed: {e}")
        return None

    events = resp.json()
    if not events:
        logger.warning("No MMA events returned from Odds API.")
        return None

    # Sort by start time
    def parse_time(ev):
        try:
            return datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
        except:
            return datetime.max

    events_sorted = sorted(events, key=parse_time)
    next_event = events_sorted[0]

    # Extract fight card from the event
    fight_card = []
    for matchup in next_event.get("competitors", []):
        # Some APIs return 2 names as an array; others return objects —
        # Normalize it
        a = matchup.get("home_team") or matchup.get("competitors", [None, None])[0]
        b = matchup.get("away_team") or matchup.get("competitors", [None, None])[1]
        if a and b:
            fight_card.append({"fighter_a": a, "fighter_b": b})

    return {
        "event_name": next_event.get("sport_title", "UFC Event"),
        "event_date": next_event.get("commence_time"),
        "location": next_event.get("venue", None),
        "fight_card": fight_card,
    }


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
