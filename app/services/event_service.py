import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

UFC_EVENTS_URL = "http://ufcstats.com/statistics/events/upcoming"

def scrape_upcoming_ufc_event():
    """
    Scrapes UFCStats for the next upcoming event.

    ALWAYS returns a dict with event_name, date, location, and fight_card,
    even if the event URL is missing (UFCStats sometimes hides it until later).
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
        logger.warning("No upcoming UFC event rows found in UFC Stats.")
        return None

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        event_name = cols[0].get_text(strip=True)
        link_tag = cols[0].find("a")
        event_href = link_tag["href"] if link_tag and link_tag.has_attr("href") else None

        date_text = cols[1].get_text(strip=True)
        location = cols[2].get_text(strip=True) or None

        # Robust date parsing
        try:
            date_obj = datetime.strptime(date_text, "%B %d, %Y")
            event_date_iso = date_obj.date().isoformat()
        except Exception:
            logger.warning(f"Could not parse date: {date_text}")
            event_date_iso = None

        event_data = {
            "event_name": event_name,
            "event_date": event_date_iso,
            "location": location,
            "event_url": event_href,
        }

        # ------------------------------
        # CASE A: No URL (today/tomorrow)
        # ------------------------------
        if not event_href:
            logger.warning(
                f"No event URL available for upcoming event '{event_name}'. "
                f"Returning partial event without fight card."
            )
            event_data["fight_card"] = []
            return event_data

        # ------------------------------
        # CASE B: Full scrape possible
        # ------------------------------
        fight_card = scrape_fight_card(event_href)
        event_data["fight_card"] = fight_card
        return event_data

    return None




def scrape_fight_card(event_url: str):
    """
    Scrapes full fight card from a UFCStats event detail page.
    Returns:
       [
         { "fighter_a": "Name", "fighter_b": "Name" }
       ]
    """
    try:
        resp = requests.get(event_url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch UFC event page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    fights = []

    # UFCStats uses several possible row types, so match both
    fight_rows = soup.select("tr.b-fight-details__table-row") or \
                  soup.select("tr.b-fight-details__table-row.b-fight-details__table-row__hover")

    for row in fight_rows:
        fighters = row.select("p.b-fight-details__person-name")

        if len(fighters) >= 2:
            fa = fighters[0].get_text(strip=True)
            fb = fighters[1].get_text(strip=True)

            if fa and fb:
                fights.append({
                    "fighter_a": fa,
                    "fighter_b": fb,
                })

    # Deduplicate any weird rows
    cleaned = []
    seen = set()

    for f in fights:
        key = f"{f['fighter_a']}__{f['fighter_b']}"
        if key not in seen:
            cleaned.append(f)
            seen.add(key)

    return cleaned

def load_next_event(db: Session):
    """
    Main entry:
    1. Scrape UFC Stats for the next upcoming event
    2. Store or update it in DB
    3. Return event JSON
    """

    data = scrape_upcoming_ufc_event()  # ← THIS MUST EXIST IN THIS FILE

    if not data:
        return None

    name = data["event_name"]

    existing = (
        db.query(Event)
        .filter(Event.event_name.ilike(name))
        .first()
    )

    if existing:
        # Update existing event
        existing.event_date = data.get("event_date")
        existing.location = data.get("location")
        existing.fight_card_json = data.get("fight_card", [])
        db.commit()
        db.refresh(existing)
        return {
            "event_name": existing.event_name,
            "event_date": existing.event_date,
            "location": existing.location,
            "fight_card": existing.fight_card_json,
        }

    # Create new event
    new_event = Event(
        event_name=data["event_name"],
        event_date=data.get("event_date"),
        location=data.get("location"),
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

