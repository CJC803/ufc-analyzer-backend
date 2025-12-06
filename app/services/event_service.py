import logging
from typing import Dict, Any, Optional, List
import requests

from sqlalchemy.orm import Session

from app.models import Event
from app.services.fighter_service import load_fighter_data
from app.services.analysis_service import analyze_matchup
from app.config import settings

logger = logging.getLogger(__name__)

UFC_EVENTS_URL = "http://ufcstats.com/statistics/events/upcoming?page=all"

# ---------------------------------------------------------
# 1. Scrape the next upcoming UFC event
# ---------------------------------------------------------
def scrape_next_event() -> Optional[Dict[str, Any]]:
    """
    Scrapes the UFCStats upcoming events page and returns:
    - event_name
    - event_date
    - location
    - fight_card (list of matchups)
    """

    try:
        html = requests.get(UFC_EVENTS_URL, timeout=10).text
    except Exception as e:
        logger.error(f"Failed to fetch upcoming events page: {e}")
        return None

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", class_="b-statistics__table-events")
    if not table:
        logger.error("Could not locate events table on UFCStats.")
        return None

    rows = table.find_all("tr")[1:]  # skip header
    if not rows:
        logger.error("No upcoming event rows found.")
        return None

    first = rows[0].find_all("td")
    if len(first) < 4:
        logger.error("Malformed event row.")
        return None

    # Basic details
    event_name = first[0].text.strip()
    event_date = first[1].text.strip()
    location = first[2].text.strip()

    # Fetch event URL to get fight card
    url_tag = rows[0].find("a")
    if not url_tag:
        logger.error("No event URL found.")
        return None

    event_url = url_tag["href"]

    fight_card = scrape_fight_card(event_url)

    return {
        "event_name": event_name,
        "event_date": event_date,
        "location": location,
        "fight_card": fight_card,
        "event_url": event_url,
    }


# ---------------------------------------------------------
# 2. Scrape the fight card for an event
# ---------------------------------------------------------
def scrape_fight_card(event_url: str) -> List[Dict[str, str]]:
    """
    Returns a list of matchups:
        [{"fighter1": "A", "fighter2": "B", "weight_class": "..."}]
    """

    try:
        html = requests.get(event_url, timeout=10).text
    except Exception as e:
        logger.error(f"Failed to fetch event page {event_url}: {e}")
        return []

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.find_all("tr", class_="b-fight-details__table-row")
    matchups = []

    for r in rows:
        cols = r.find_all("td")
        if len(cols) < 2:
            continue

        f1 = cols[1].text.strip()
        f2 = cols[2].text.strip()

        weight_class = cols[0].text.strip()

        matchups.append({
            "fighter1": f1,
            "fighter2": f2,
            "weight_class": weight_class
        })

    return matchups


# ---------------------------------------------------------
# 3. Create an event in the database
# ---------------------------------------------------------
def create_event(db: Session, event_data: Dict[str, Any]) -> Event:
    event = Event(
        event_name=event_data["event_name"],
        event_date=event_data["event_date"],
        location=event_data["location"],
        fight_card_json=event_data["fight_card"],
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(f"Created event: {event.event_name}")
    return event


# ---------------------------------------------------------
# 4. Get or refresh the next event
# ---------------------------------------------------------
def get_next_event(db: Session) -> Event:
    """
    Always returns the next upcoming UFC event.
    If not stored, scrape + create.
    """
    latest = db.query(Event).order_by(Event.id.desc()).first()

    if latest:
        logger.info(f"Using cached event: {latest.event_name}")
        return latest

    scraped = scrape_next_event()
    if not scraped:
        raise RuntimeError("Could not load next UFC event.")

    return create_event(db, scraped)


# ---------------------------------------------------------
# 5. Analyze every matchup on a fight card
# ---------------------------------------------------------
def analyze_event_fights(db: Session, event_id: int) -> List[Dict[str, Any]]:
    """
    Loops through every matchup in the event and produces:
      {
        "fighter1": "...",
        "fighter2": "...",
        "analysis": { full GPT output }
      }
    """

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError("Event not found.")

    results = []

    for fight in event.fight_card_json:
        f1 = fight["fighter1"]
        f2 = fight["fighter2"]

        logger.info(f"Analyzing matchup: {f1} vs {f2}")

        analysis = analyze_matchup(db, f1, f2)

        results.append({
            "fighter1": f1,
            "fighter2": f2,
            "weight_class": fight.get("weight_class"),
            "analysis": analysis
        })

    return results
