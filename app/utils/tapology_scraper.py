import logging
from typing import Optional, Dict, Any

from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# GPT Fallback: resolve Tapology fighter slug
# ---------------------------------------------------------

def _gpt_find_tapology_slug(name: str) -> Optional[str]:
    """
    GPT resolves only the Tapology fighter URL slug.
    Example:
      Input: "Jon Jones"
      Output: "jon-jones"   (not the full URL)
    """

    prompt = (
        f"Give ONLY the Tapology.com fighter slug for the fighter '{name}'. "
        f"Example: For 'Jon Jones' return: jon-jones "
        f"If unknown return ONLY 'null'. No extra text."
    )

    raw = gpt_safe_call([{"role": "user", "content": prompt}])

    if not raw:
        return None

    raw = raw.strip().lower()

    if raw == "null":
        return None

    # slug should not contain a URL, just the slug string
    if "/" in raw:
        raw = raw.split("/")[-1]

    return raw


# ---------------------------------------------------------
# Placeholder Tapology scraper
# Real scraping requires JS rendering / Cloudflare bypass
# ---------------------------------------------------------

def _scrape_tapology_profile(slug: str) -> Optional[Dict[str, Any]]:
    """
    Returns a placeholder Tapology profile object.
    This prevents backend crashes until we add full Tapology scraping.
    """

    logger.info(f"Tapology placeholder used for slug: {slug}")

    return {
        "tapology_slug": slug,
        "tapology_url": f"https://www.tapology.com/fightcenter/fighters/{slug}",
        "note": "Tapology scraping not implemented yet. Slug resolved successfully.",
    }


# ---------------------------------------------------------
# Public API: get Tapology fighter data
# ---------------------------------------------------------

def get_tapology_profile(name: str) -> Optional[Dict[str, Any]]:
    """
    1. Resolve slug via GPT
    2. Return placeholder scraped data
    """

    logger.info(f"Resolving Tapology profile for: {name}")

    slug = _gpt_find_tapology_slug(name)

    if not slug:
        logger.warning(f"No Tapology slug found for fighter: {name}")
        return None

    return _scrape_tapology_profile(slug)
