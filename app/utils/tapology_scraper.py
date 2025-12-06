import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

TAPOLOGY_SEARCH = "https://www.tapology.com/search?term="


def fetch_tapology_fighter(name: str) -> Optional[Dict[str, Any]]:
    """
    Searches Tapology for a fighter and scrapes basic profile data.
    Returns None if no profile found or scrape fails.
    """

    try:
        url = TAPOLOGY_SEARCH + requests.utils.quote(name)
        logger.info(f"[Tapology] Searching: {url}")

        html = requests.get(url, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        # -----------------------------
        # Locate fighter search results
        # -----------------------------
        fighter_link = soup.select_one(".fighterResult .name a")
        if not fighter_link:
            logger.warning(f"[Tapology] No fighter found for: {name}")
            return None

        profile_url = "https://www.tapology.com" + fighter_link.get("href")

        # -----------------------------
        # Scrape fighter profile
        # -----------------------------
        logger.info(f"[Tapology] Scraping profile: {profile_url}")
        profile_html = requests.get(profile_url, timeout=10).text
        psoup = BeautifulSoup(profile_html, "html.parser")

        # Fighter name
        title = psoup.select_one(".fighterPage h1")
        fighter_name = title.text.strip() if title else name

        # Record / details
        record_elem = psoup.select_one(".fighterRecord span.record")
        record = record_elem.text.strip() if record_elem else None

        height_elem = psoup.find("li", string=lambda s: s and "Height" in s)
        reach_elem = psoup.find("li", string=lambda s: s and "Reach" in s)

        height = height_elem.text.replace("Height:", "").strip() if height_elem else None
        reach = reach_elem.text.replace("Reach:", "").strip() if reach_elem else None

        return {
            "name": fighter_name,
            "profile_url": profile_url,
            "record": record,
            "height": height,
            "reach": reach,
        }

    except Exception as e:
        logger.error(f"[Tapology] Scraper failed for {name}: {e}")
        return None
