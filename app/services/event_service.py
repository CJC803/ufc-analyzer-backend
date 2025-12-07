import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

UFC_EVENTS_URL = "http://ufcstats.com/statistics/events/upcoming"


def scrape_upcoming_ufc_event():
    """
    Scrapes UFCStats for the next upcoming event.
    Returns:
        {
          "event_name": str,
          "event_date": str (ISO),
          "location": str or None,
          "fight_card": [ { fighter_a, fighter_b } ]
        }
    or None
    """
    try:
        resp = requests.get(UFC_EVENTS_URL, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch UFC events page: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # UFC Stats upcoming page uses this table for events
    rows = soup.select("table.b-statistics__table-events tbody tr")

    if not rows:
        logger.warning("No upcoming event rows found in UFC Stats.")
        return None

    next_event = None

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue

        event_name = cols[0].get_text(strip=True)
        event_href = cols[0].find("a")["href"] if cols[0].find("a") else None

        date_text = cols[1].get_text(strip=True)
        location = cols[2].get_text(strip=True)

        # Parse date safely
        try:
            date_obj = datetime.strptime(date_text, "%B %d, %Y")
            event_date_iso = date_obj.isoformat()
        except:
            event_date_iso = None

        next_event = {
            "event_name": event_name,
            "event_date": event_date_iso,
            "location": location or None,
            "event_url": event_href,
        }
        break  # first row == closest event

    if not next_event or not next_event.get("event_url"):
        logger.warning("Event found but no event URL available.")
        return None

    # Pull full card
    card = scrape_fight_card(next_event["event_url"])

    next_event["fight_card"] = card
    return next_event



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
