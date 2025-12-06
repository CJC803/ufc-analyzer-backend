import logging
from typing import List, Dict, Any, Optional

from app.utils.tapology_scraper import fetch_tapology_fighter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Batch lookup (safe, non-blocking)
# ---------------------------------------------------------
def get_tapology_batch(names: List[str]) -> List[Dict[str, Any]]:
    """
    Accepts a list of fighter names.
    Returns a list of dicts containing Tapology data.
    Failed lookups still return an entry with error message.
    """

    results: List[Dict[str, Any]] = []

    logger.info(f"Running Tapology batch lookup for {len(names)} fighters...")

    for name in names:
        name_clean = name.strip()
        logger.info(f"[Tapology Batch] Fetching: {name_clean}")

        try:
            data = fetch_tapology_fighter(name_clean)

            if not data:
                logger.warning(f"No Tapology data found for '{name_clean}'.")
                results.append(
                    {
                        "name": name_clean,
                        "tapology": None,
                        "error": "Lookup failed or no profile found"
                    }
                )
                continue

            # Wrap response in a consistent envelope
            results.append(
                {
                    "name": name_clean,
                    "tapology": data,
                    "error": None
                }
            )

        except Exception as e:
            logger.error(f"Tapology batch error for '{name_clean}': {e}")

            results.append(
                {
                    "name": name_clean,
                    "tapology": None,
                    "error": str(e)
                }
            )

    logger.info(f"Tapology batch complete: {len(results)} responses.")

    return results


# ---------------------------------------------------------
# Optional helper: pretty print results in logs
# ---------------------------------------------------------
def log_batch_summary(results: List[Dict[str, Any]]):
    """
    Just a helper for debugging in console/logs.
    """
    total = len(results)
    ok = sum(1 for r in results if r["tapology"])
    fail = total - ok

    logger.info(f"[Tapology Batch Summary] Total: {total} | Success: {ok} | Fail: {fail}")
