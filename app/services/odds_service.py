import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def get_odds_for_matchups(fight_card: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Temporary placeholder implementation.
    Returns neutral (-110/-110) odds for each fight so the app can boot.
    Replace with real odds scraping later.
    """
    logger.warning("Using placeholder odds data (no real odds source yet).")

    results = []
    for fight in fight_card:
        results.append({
            "fighter_a": fight.get("fighter_a"),
            "fighter_b": fight.get("fighter_b"),
            "odds_a": -110,
            "odds_b": -110,
            "source": "placeholder"
        })

    return results
