import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from app.models import Event  # ← REQUIRED IMPORT

logger = logging.getLogger(__name__)

UFC_EVENTS_URL = "http://ufcstats.com/statistics/events/upcoming"


# ---------------------------------------------------------
# SCRAPE NEXT UPCOMING EVENT
# ---------------------------------------------------------
def scrape_upcoming_ufc_event():
    """
    Scrapes UFCStats for the next upcoming event.
    ALWAYS returns a dict with event_name, event_date, location, and fight_card
    unless the page is truly empty.
    """

    try:
        resp = requests.get(UFC_EVENTS_URL, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch UFC events page: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    rows = soup.select("table.b-statistics__table-events tbody tr")

    if not rows:
        logger.warning("No upcoming event rows found in UFC Stats.")
        return None

    # Get FIRST event only
    row = rows[0]
    cols = row.find_all("td")

    if len(cols) < 3:
        logger.warning("Row found but missing columns.")
        return None

    event_name = cols[0].get_text(strip=True)
    link_tag = cols[0].find("a")
    event_href = link_tag["href"] if link_tag and link_tag.has_attr("href") else None

    date_text = cols[1].get_text(strip=True)
    location = cols[2].get_text(strip=True) or None

    # Safe date parsing
    try:
        dt = datetime.strptime(date_text, "%B %d, %Y")
        event_date_iso = dt.date().isoformat()
    except:
        logger.warning(f"Could not parse event date: {date_text}")
        event_date_iso = None

    event_data = {
        "event_name": event_name,
        "event_date": event_date_iso,
        "location": location,
        "event_url": event_href,
    }

    # -----------------------------------------
    # If no event URL, return partial event
    # -----------------------------------------
    if not event_href:
        logger.warning(
            f"No event URL available for '{event_name}'. Returning partial event."
        )
        event_data["fight_card"] = []
        return event_data

    # Scrape fight card if URL exists
    event_data["fight_card"] = scrape_fight_card(event_href)
    return event_data


# ---------------------------------------------------------
# SCRAPE FIGHT CARD FOR AN EVENT PAGE
# ---------------------------------------------------------
def scrape_fight_card(event_url: str):
    try:
        resp = requests.get(event_url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch UFC event page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    rows = soup.select("tr.b-fight-details__table-row") or \
           soup.select("tr.b-fight-details__table-row.b-fight-details__table-row__hover")

    fights = []

    for row in rows:
        fighters = row.select("p.b-fight-details__person-name")
        if len(fighters) >= 2:
            f1 = fighters[0].get_text(strip=True)
            f2 = fighters[1].get_text(strip=True)

            if f1 and f2:
                fights.append({"fighter_a": f1, "fighter_b": f2})

    # Deduplicate
    seen = set()
    cleaned = []

    for f in fights:
        key = f"{f['fighter_a']}__{f['fighter_b']}"
        if key not in seen:
            cleaned.append(f)
            seen.add(key)

    return cleaned


# ---------------------------------------------------------
# LOAD + STORE NEXT EVENT IN DB
# ---------------------------------------------------------
def load_next_event(db: Session):
    data = scrape_upcoming_ufc_event()

    if not data:
        return None

    name = data["event_name"]

    existing = (
        db.query(Event)
        .filter(Event.event_name.ilike(name))
        .first()
    )

    if existing:
        existing.event_date = data["event_date"]
        existing.location = data["location"]
        existing.fight_card_json = data.get("fight_card", [])
        db.commit()
        db.refresh(existing)

        return {
            "event_name": existing.event_name,
            "event_date": existing.event_date,
            "location": existing.location,
            "fight_card": existing.fight_card_json,
        }

    new_event = Event(
        event_name=data["event_name"],
        event_date=data["event_date"],
        location=data["location"],
        fight_card_json=data.get("fight_card", []),
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return {
        "event_name": new_event.event_name,
        "event_date": new_event.event_date,
        "location": new_event.location,
        "fight_card": new_event.fight_card_json,
    }
