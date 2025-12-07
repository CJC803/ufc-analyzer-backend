import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models import Event
from bs4 import BeautifulSoup
import requests
import datetime

logger = logging.getLogger(__name__)

UFC_STATS_EVENTS_URL = "http://ufcstats.com/statistics/events/upcoming"


# ------------------------------------------------------
# Scrape all upcoming UFC events
# ------------------------------------------------------
def scrape_upcoming_events() -> List[Dict[str, Any]]:
    resp = requests.get(UFC_STATS_EVENTS_URL, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    rows = soup.select("table.b-statistics__table-events tbody tr")

    events = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        name = cols[0].get_text(strip=True)
        date_str = cols[2].get_text(strip=True)
        location = cols[3].get_text(strip=True)

        # Convert date
        try:
            event_dt = datetime.datetime.strptime(date_str, "%B %d, %Y")
        except Exception:
            event_dt = None

        events.append({
            "event_name": name,
            "event_date": event_dt.isoformat() if event_dt else None,
            "location": location,
            "fight_card": []  # We fill this separately next
        })

    return events


# ------------------------------------------------------
# Pick earliest future event
# ------------------------------------------------------
def get_next_event(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    now = datetime.datetime.utcnow()

    future = [
        e for e in events
        if e["event_date"] is not None and datetime.datetime.fromisoformat(e["event_date"]) > now
    ]

    if not future:
        return None

    # sort by date asc
    future.sort(key=lambda e: e["event_date"])
    return future[0]


# ------------------------------------------------------
# Save or update event in DB
# ------------------------------------------------------
def get_event_by_name(db: Session, name: str) -> Optional[Event]:
    return db.query(Event).filter(Event.event_name.ilike(name)).first()


def save_event(db: Session, data: Dict[str, Any]) -> Event:
    existing = get_event_by_name(db, data["event_name"])

    if existing:
        existing.event_date = data["event_date"]
        existing.location = data["location"]
        existing.fight_card_json = data["fight_card"]
        db.commit()
        db.refresh(existing)
        return existing

    new_event = Event(
        event_name=data["event_name"],
        event_date=data["event_date"],
        location=data["location"],
        fight_card_json=data["fight_card"],
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


# ------------------------------------------------------
# Public: return ALL upcoming events
# ------------------------------------------------------
def load_all_upcoming_events(db: Session) -> List[Dict[str, Any]]:
    scraped = scrape_upcoming_events()

    saved = []
    for evt in scraped:
        saved_evt = save_event(db, evt)
        saved.append({
            "event_name": saved_evt.event_name,
            "event_date": saved_evt.event_date,
            "location": saved_evt.location,
            "fight_card": saved_evt.fight_card_json or [],
        })

    return saved


# ------------------------------------------------------
# Public: return the next event
# ------------------------------------------------------
def load_next_event(db: Session) -> Optional[Dict[str, Any]]:
    events = scrape_upcoming_events()
    next_evt = get_next_event(events)

    if not next_evt:
        return None

    saved = save_event(db, next_evt)

    return {
        "event_name": saved.event_name,
        "event_date": saved.event_date,
        "location": saved.location,
        "fight_card": saved.fight_card_json or [],
    }
    import re
import requests
from bs4 import BeautifulSoup

UFC_EVENT_DETAILS_BASE = "http://ufcstats.com/event-details/"

def extract_event_id(event_name: str, soup: BeautifulSoup):
    """
    Scrapes the event row to grab the DOM link which contains the event ID.
    Example href:
    http://ufcstats.com/event-details/9b158a41ff75984a
    """
    link = soup.find("a", string=re.compile(event_name, re.I))
    if not link:
        return None
    href = link.get("href", "")
    return href.split("/")[-1] if "event-details" in href else None


def scrape_fight_card(event_id: str):
    """
    Scrape fighters from the event details page.
    Returns:
        [ { "fighter_a": "", "fighter_b": "" }, ... ]
    """
    url = UFC_EVENT_DETAILS_BASE + event_id
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")

    fight_rows = soup.select("tbody tr.b-fight-details__table-row")
    fights = []

    for row in fight_rows:
        fighters = row.select("a.b-link.b-link_style_black")
        if len(fighters) >= 2:
            a = fighters[0].get_text(strip=True)
            b = fighters[1].get_text(strip=True)
            fights.append({"fighter_a": a, "fighter_b": b})

    return fights

