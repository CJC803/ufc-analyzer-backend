import logging
from typing import List, Dict, Any

from app.utils.tapology_scraper import fetch_tapology_fighter

logger = logging.getLogger(__name__)


def get_tapology_batch(names: List[str]) -> List[Dict[str, Any]]:
    """
    Batch Tapology lookup.
    Each fighter name returns {name, tapology: {...} or None, error or None}
    """

    results: List[Dict[str, Any]] = []

    logger.info(f"[Tapology Batch] Starting lookup for {len(names)} fighters...")

    for name in names:
        clean = name.strip()
        logger.info(f"[Tapology Batch] Fetching '{clean}'")

        try:
            data = fetch_tapology_fighter(clean)
            results.append(
                {
                    "name": clean,
                    "tapology": data,
                    "error": None if data else "Profile not found"
                }
            )
        except Exception as e:
            logger.error(f"[Tapology Batch] Error for '{clean}': {e}")
            results.append(
                {
                    "name": clean,
                    "tapology": None,
                    "error": str(e)
                }
            )

    logger.info(f"[Tapology Batch] Complete.")
    return results
