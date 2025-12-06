import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_tapology_batch(fighter_names: List[str]) -> List[Dict[str, Any]]:
    """
    Placeholder Tapology batch fetch.
    Returns empty metadata so the app can run.
    
    Replace with real scraping or API integration later.
    """
    logger.warning("Using placeholder Tapology batch fetch (no real data yet).")

    results = []
    for name in fighter_names:
        results.append({
            "name": name,
            "tapology_slug": None,
            "tapology_json": None,
            "source": "placeholder"
        })

    return results
