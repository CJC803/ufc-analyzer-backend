import logging
from typing import Dict, Any, List

from app.services.odds_service import get_odds_for_matchups

logger = logging.getLogger(__name__)


# ---------------------------------------------
# STEP 1 — Extract structured matchup features
# ---------------------------------------------
def compute_stats_features(event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Input: event_data = {
        'event_name': str,
        'fight_card': [
            {
                'fighter_a': str,
                'fighter_b': str,
                'weight_class': str | None
            }
        ]
    }

    Output: List of enriched matchup dicts, with odds injected.
    """

    if "fight_card" not in event_data:
        logger.error("event_data missing fight_card.")
        return []

    matchups = event_data["fight_card"]

    # Build a simple pair list for the odds service
    fighter_pairs = [
        {
            "fighter_a": m["fighter_a"],
            "fighter_b": m["fighter_b"]
        }
        for m in matchups
    ]

    # Fetch betting odds (or placeholder)
    odds_lookup = get_odds_for_matchups(fighter_pairs)

    enriched = []

    for m in matchups:
        key = f"{m['fighter_a']} vs {m['fighter_b']}"

        odds = odds_lookup.get(key, {
            "fighter_a_odds": None,
            "fighter_b_odds": None,
            "source": "none"
        })

        enriched.append({
            "fighter_a": m["fighter_a"],
            "fighter_b": m["fighter_b"],
            "weight_class": m.get("weight_class"),
            "odds": odds
        })

    return enriched


# --------------------------------------------------------
# STEP 2 — Construct GPT prompt from structured features
# --------------------------------------------------------
def build_analysis_prompt(event_name: str, fight_features: List[Dict[str, Any]]) -> str:
    """
    Convert structured features → a GPT analysis prompt
    """

    if not fight_features:
        return "No fight matchups were provided."

    lines = []
    lines.append(f"Analyze the upcoming UFC event: {event_name}.")
    lines.append("Provide detailed breakdowns for each matchup including:")
    lines.append("- Stylistic matchup assessment")
    lines.append("- Paths to victory")
    lines.append("- Betting market interpretation")
    lines.append("- Predicted winner and method")
    lines.append("")
    lines.append("Here is the structured data:")

    for f in fight_features:
        lines.append("\n--- MATCHUP ---")
        lines.append(f"Fighter A: {f['fighter_a']}")
        lines.append(f"Fighter B: {f['fighter_b']}")
        lines.append(f"Weight Class: {f.get('weight_class')}")

        odds = f["odds"]
        lines.append(f"Odds (A): {odds.get('fighter_a_odds')}")
        lines.append(f"Odds (B): {odds.get('fighter_b_odds')}")
        lines.append(f"Odds Source: {odds.get('source')}")

    lines.append("\nNow provide your expert-level fight predictions:")

    return "\n".join(lines)
