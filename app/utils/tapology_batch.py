import logging
from typing import List, Dict, Any, Optional

from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# GPT fallback: Ask for Tapology fighter slug
# ---------------------------------------------------------

def _gpt_find_tapology_slug(name: str) -> Optional[str]:
    """
    Asks GPT to return ONLY a Tapology slug for this fighter.
    Example:
        Input: "Conor McGregor"
        Output: "conor-mcgregor"
    If unknown → return None
    """
    prompt = (
        f"Return ONLY the Tapology.com fighter slug for '{name}'. "
        f"Example: 'jon-jones'. "
        f"If unknown, reply exactly with 'null'. No explanation."
    )

    raw = gpt_safe_call([{"role": "user", "content": prompt}])
    if not raw:
        return None

    raw = raw.strip().lower()

    if raw == "null":
        return None

    # basic slug sanity check
    if " " in raw or "/" in raw:
        return None

    return raw


# ---------------------------------------------------------
# Placeholder scraping function (future upgradeable)
# ---------------------------------------------------------

def _scrape_tapology_profile(slug: str) -> Optional[Dict[str, Any]]:
    """
    Placeholder scraper until Tapology scraping is implemented.
    We return a minimal structure so the backend NEVER crashes.
    """

    # Future scraping plan:
    # url = f"https://www.tapology.com/fightcenter/fighters/{slug}"
    # html = requests.get(url)...

    logger.info(f"Tapology scrape placeholder: {slug}")

    return {
        "slug": slug,
        "tapology_url": f"https://www.tapology.com/fightcenter/fighters/{slug}",
        "note": "Tapology scraping not implemented yet. Slug resolved successfully.",
    }


# ---------------------------------------------------------
# Public API: Get single profile
# ---------------------------------------------------------

def get_tapology_profile(name: str) -> Optional[Dict[str, Any]]:
    """
    Attempts to resolve a Tapology fighter profile:
    1. Ask GPT for slug
    2. If slug found → return placeholder data (or real scrape later)
    """
    logger.info(f"Resolving Tapology profile for: {name}")

    slug = _gpt_find_tapology_slug(name)
    if not slug:
        logger.warning(f"Tapology slug not found for: {name}")
        return None

    return _scrape_tapology_profile(slug)


# ---------------------------------------------------------
# Public API: Batch lookup
# ---------------------------------------------------------

def get_tapology_batch(names: List[str]) -> Dict[str, Any]:
    """
    Looks up multiple fighters at once from Tapology.

    Returns:
    {
        "results": {
            "Conor McGregor": {...},
            "Jon Jones": {...}
        },
        "failed": ["Unknown Dude"]
    }
    """
    logger.info(f"Running Tapology batch lookup for {len(names)} fighters...")

    results: Dict[str, Any] = {}
    failed: List[str] = []

    for name in names:
        try:
            profile = get_tapology_profile(name)

            if profile:
                results[name] = profile
            else:
                failed.append(name)

        except Exception as e:
            logger.error(f"Tapology batch error for {name}: {e}")
            failed.append(name)

    return {
        "results": results,
        "failed": failed,
    }
