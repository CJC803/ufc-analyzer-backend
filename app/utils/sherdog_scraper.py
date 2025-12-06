import logging
from typing import Optional, Dict, Any

from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# GPT fallback: Ask for Sherdog fighter URL
# ---------------------------------------------------------

def _gpt_find_sherdog_url(name: str) -> Optional[str]:
    """
    Uses GPT to return ONLY a Sherdog fighter profile URL.
    Example:
        Input: "Jon Jones"
        Output: "https://www.sherdog.com/fighter/Jon-Jones-27944"
    
    If unknown → returns None.
    """
    prompt = (
        f"Give me the EXACT Sherdog.com fighter profile URL for: '{name}'. "
        f"Example: 'https://www.sherdog.com/fighter/Jon-Jones-27944'. "
        f"If unknown return ONLY 'null'. No extra text."
    )

    raw = gpt_safe_call([{"role": "user", "content": prompt}])
    if not raw:
        return None

    raw = raw.strip().lower()

    if raw == "null":
        return None

    if raw.startswith("http"):
        return raw

    return None


# ---------------------------------------------------------
# Placeholder Sherdog scraper (upgradeable later)
# ---------------------------------------------------------

def _scrape_sherdog_profile(url: str) -> Optional[Dict[str, Any]]:
    """
    Placeholder scraper — real scraping requires Cloudflare bypass.
    For now, we return a structured placeholder object.
    """

    logger.info(f"Sherdog scrape placeholder used for URL: {url}")

    return {
        "sherdog_url": url,
        "note": "Sherdog scraping not implemented yet. URL resolved successfully.",
    }


# ---------------------------------------------------------
# Public API: Lookup a single Sherdog profile
# ---------------------------------------------------------

def get_sherdog_profile(name: str) -> Optional[Dict[str, Any]]:
    """
    1. Uses GPT to resolve the fighter's Sherdog profile URL.
    2. Returns placeholder parsed data.
    """

    logger.info(f"Resolving Sherdog profile for: {name}")

    url = _gpt_find_sherdog_url(name)

    if not url:
        logger.warning(f"No Sherdog URL found for: {name}")
        return None

    return _scrape_sherdog_profile(url)
