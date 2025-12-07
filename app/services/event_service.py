import logging
import os
import json
import re
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from app.models import Event
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------------

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
EVENTS_ENDPOINT = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/events"

if not THE_ODDS_API_KEY:
    logger.error("Missing THE_ODDS_API_KEY environment variable!")


# -------------------------------------------------------------------
# JSON Extraction Helper
# -------------------------------------------------------------------

def extract_json_block(text: str) -> str:
    """Extract valid JSON from GPT responses."""
    fenced = re.search(r"```(?:json)?(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return brace.group(0).strip()

    return text.strip()


# -------------------------------------------------------------------
# DB Query Helper
# -------------------------------------------------------------------

def get_event_by_name(db: Session, name: str):
    return (
        db.query(Event)
        .filter(Event.event_name.ilike(name.strip()))
        .first()
    )


# -------------------------------------------------------------------
# Odds API Fetcher (PRIMARY SOURCE)
# -------------------------------------------------------------------

def fetch_event_from_odds_api() -> dict | None:
    """Fetch the *next upcoming* UFC/MMA event from The Odds API."""
    try:
        res = requests.get(
            EVENTS_ENDPOINT,
            params={"apiKey": THE_ODDS_API_KEY},
            timeout=10,
        )
        res.raise_for_status()
        events = res.json()

        if not events:
            return None

        # Convert events into (date, event_json) tuples
        cleaned = []
        for ev in events:
            try:
                dt = datetime.fromisoformat(
                    ev["commence_time"].replace("Z", "+00:00")
                )
                cleaned.append((dt, ev))
            except Exception:
                continue

        future_events = [(dt, ev) for dt, ev in cleaned if dt > datetime.now(timezone.utc)]
        if not future_events:
            return None

        # Pick earliest
        next_dt, next_ev = sorted(future_events, key=lambda x: x[0])[0]

        fight_card = []
        if "bookmakers" in next_ev:
            # optional; odds API doesn't always include fighters list cleanly
            pass

        return {
            "event_name": next_ev.get("sport_title", "MMA Event"),
            "event_date": next_dt.isoformat(),
            "location": None,  # The Odds API doesn’t provide locations
            "fight_card": fight_card,
        }

    except Exception as e:
        logger.error(f"Error fetching event from Odds API: {e}")
        return None


# -------------------------------------------------------------------
# GPT Fallback When Odds API Fails
# -------------------------------------------------------------------

def fetch_event_from_gpt() -> dict | None:
    prompt = """
Return ONLY the upcoming NEXT UFC numbered PPV or Fight Night event.
Must be PURE JSON, EXACT format:

{
  "event_name": "",
  "event_date": "",
  "location": "",
  "fight_card": [
    {"fighter_a": "", "fighter_b": ""}
  ]
}

Rules:
- Must be a real scheduled future UFC event.
- event_date must be ISO format (YYYY-MM-DD).
- No commentary, no markdown, no explanation.
"""

    raw = gpt_safe_call([prompt])
    clean = extract_json_block(raw)

    logger.info("======= CLEAN GPT EVENT RESPONSE =======")
    logger.info(clean)
    logger.info("========================================")

    try:
        data = json.loads(clean)
    except Exception as e:
        logger.error(f"GPT fallback JSON parse error: {e}")
        return None

    # Filter out garbage dates / past events
    try:
        dt = datetime.fromisoformat(data["event_date"])
        if dt < datetime.now():
            logger.warning("GPT returned past event — discarding.")
            return None
    except Exception:
        logger.warning("GPT returned invalid date — discarding.")
        return None

    return data


# -------------------------------------------------------------------
# DB Insert/Update Helpers
# -------------------------------------------------------------------

def create_event(db: Session, data: dict) -> Event:
    event = Event(
        event_name=data["event_name"],
        event_date=data.get("event_date"),
        location=data.get("location"),
        fight_card_json=data.get("fight_card"),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event: Event, data: dict) -> Event:
    event.event_name = data["event_name"]
    event.event_date = data.get("event_date")
    event.location = data.get("location")
    event.fight_card_json = data.get("fight_card")

    db.commit()
    db.refresh(event)
    return event


def event_to_json(event: Event) -> dict:
    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "location": event.location,
        "fight_card": event.fight_card_json or [],
    }


# -------------------------------------------------------------------
# MAIN ENTRYPOINT — Get, Save, Return the Next Event
# -------------------------------------------------------------------

def load_next_event(db: Session) -> dict | None:

    # Step 1 — Try The Odds API FIRST
    event_data = fetch_event_from_odds_api()

    # Step 2 — If Odds API fails or returns nothing, fallback to GPT
    if not event_data:
        logger.warning("Odds API returned nothing. Using GPT fallback.")
        event_data = fetch_event_from_gpt()

    if not event_data:
        return None

    name = event_data["event_name"]
    existing = get_event_by_name(db, name)

    if existing:
        event = update_event(db, existing, event_data)
    else:
        event = create_event(db, event_data)

    return event_to_json(event)
