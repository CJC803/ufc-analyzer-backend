import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional

from app.schemas import EventRead, FightPair
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

UFC_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"
UFC_BASE = "http://ufcstats.com"


# ---------------------------------------------------------
# GPT Fallback
# ---------------------------------------------------------

def gpt_fallback_next_event() -> EventRead:
    """
    If scraping UFCStats fails, query GPT for the next UFC event.
    """
    prompt = (
        "What is the next upcoming UFC event? "
        "Give me ONLY JSON in this format:\n"
        "{"
        "  'event_name': str,"
        "  'event_date': str,"
        "  'location': str,"
        "  'fight_card': [ {'fighter_a': str, 'fighter_b': str} ]"
        "}"
    )

    raw = gpt_safe_call([
        {"role": "user", "content": prompt}
    ])

    # Parse GPT output
    try:
        data = eval(raw)  # (acceptable only because GPT is constrained)
    except Exception:
        logger.error("GPT fallback returned malformed JSON.")
        raise RuntimeError("GPT fallback failed: invalid JSON")

    fight_pairs = [
        FightPair(
            fighter_a=item["fighter_a"],
            fighter_b=item["fighter_b"],
            weight_class=None
        )
        for item in data["fight_card"]
    ]

    return EventRead(
        event_name=data["event_name"],
        event_date=data.get("event_date"),
        location=data.get("location"),
        fight_card=fight_pairs
    )


# ---------------------------------------------------------
# Scrape upcoming event URL
# ---------------------------------------------------------

def scrape_event_url() -> Optional[str]:
    """
    Scrape UFCStats Upcoming Events table and return the FIRST event's URL.
    """
    logger.info("Scraping UFCStats upcoming events...")

    try:
        html = requests.get(UFC_UPCOMING, timeout=10).text
    except Exception as e:
        logger.error(f"Failed to fetch UFC upcoming events: {e}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="b-statistics__table-events")

    if not table:
        logger.error("Could not find events table on UFCStats.")
        return None

    rows = table.find_all("tr")[1:]
    if not rows:
        logger.error("No event rows found.")
        return None

    cols = rows[0].find_all("td")
    if not cols:
        return None

    link = cols[0].find("a")
    if not link:
        return None

    return link["href"]


# ---------------------------------------------------------
# Scrape event details page
# ---------------------------------------------------------

def scrape_event_details(event_url: str) -> Optional[EventRead]:
    """
    Given an event URL from UFCStats, scrape the fight card.
    """
    logger.info(f"Scraping event page: {event_url}")

    try:
        html = requests.get(event_url, timeout=10).text
    except Exception as e:
        logger.error(f"Failed to fetch event page: {e}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Metadata
    header = soup.find("span", class_="b-content__title-highlight")
    event_name = header.get_text(strip=True) if header else "Unknown Event"

    date_elem = soup.find("li", class_="b-list__box-list-item")
    event_date = date_elem.get_text(strip=True).replace("Date:", "").strip() if date_elem else None

    location_elem = soup.find_all("li", class_="b-list__box-list-item")
    location = None
    if len(location_elem) > 1:
        location = location_elem[1].get_text(strip=True).replace("Location:", "").strip()

    # Fight card
    fight_pairs: List[FightPair] = []

    table = soup.find("tbody", class_="b-fight-details__table-body")
    if not table:
        logger.error("No fight table found on UFC event page.")
        return None

    rows = table.find_all("tr", class_="b-fight-details__table-row")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 2:
            continue

        fighters = cols[1].find_all("a", class_="b-link")
        if len(fighters) != 2:
            continue

        fighter_a = fighters[0].text.strip()
        fighter_b = fighters[1].text.strip()

        weight_class_elem = cols[0].find("p")
        weight_class = weight_class_elem.text.strip() if weight_class_elem else None

        fight_pairs.append(
            FightPair(
                fighter_a=fighter_a,
                fighter_b=fighter_b,
                weight_class=weight_class
            )
        )

    return EventRead(
        event_name=event_name,
        event_date=event_date,
        location=location,
        fight_card=fight_pairs
    )


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------

def get_next_ufc_event() -> EventRead:
    """
    Main function:
    1. Try scraping UFCStats upcoming → event URL
    2. Try scraping the event page → fight card
    3. If anything fails → GPT fallback
    """
    logger.info("Determining next UFC event...")

    try:
        event_url = scrape_event_url()
        if not event_url:
            raise RuntimeError("Failed to find event URL")

        event_data = scrape_event_details(event_url)
        if not event_data:
            raise RuntimeError("Failed to parse event page")

        return event_data

    except Exception as e:
        logger.error(f"Scraping failed, using GPT fallback. Reason: {e}")
        return gpt_fallback_next_event()

