import logging
import re
import json
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models import Event
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# -----------------------------------
# Odds API configuration
# -----------------------------------
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
EVENTS_ENDPOINT = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/events"

if not ODDS_API_KEY:
    logger.error("ODDS_API_KEY is missing! Set it in Railway environment variables.")
    
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
from datetime import datetime, timezone

def _fetch_next_event_from_odds_api() -> Optional[Dict[str, Any]]:
    """
    Uses The Odds API to fetch REAL upcoming MMA events.
    Returns ONLY events that have not yet started (UTC aware).
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

    now_utc = datetime.now(timezone.utc)

    upcoming = []
    for ev in events:
        raw_time = ev.get("commence_time")
        if not raw_time:
            continue

        try:
            event_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except:
            continue

        # ONLY keep events whose start time is still in the future
        if event_time > now_utc:
            upcoming.append((event_time, ev))

    if not upcoming:
        logger.warning("No future MMA events found.")
        return None

    # Pick the nearest upcoming event
    upcoming.sort(key=lambda x: x[0])
    next_event_time, next_event = upcoming[0]

    fight_card = []
    for matchup in next_event.get("competitors", []):
        a = matchup.get("home_team") or matchup.get("competitors", [None, None])[0]
        b = matchup.get("away_team") or matchup.get("competitors", [None, None])[1]
        if a and b:
            fight_card.append({"fighter_a": a, "fighter_b": b})

    return {
        "event_name": next_event.get("sport_title", "MMA Event"),
        "event_date": next_event_time.isoformat(),
        "location": next_event.get("venue"),
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
    gpt_data = _fetch_next_event_from_odds_api()
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
