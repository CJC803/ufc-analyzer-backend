import logging
from typing import Dict, Any, List

from app.services.fighter_service import load_fighter_data
from app.services.odds_service import get_odds_for_matchups

logger = logging.getLogger(__name__)


# -------------------------------------------------------------
# Compute stat features from fighter metadata
# -------------------------------------------------------------
def compute_stats_features(f1: Dict[str, Any], f2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts scraped fighter metadata into normalized
    numbers and comparison features.
    """

    # Safety defaults to prevent crashes
    f1 = f1 or {}
    f2 = f2 or {}

    def safe_num(value):
        try:
            return float(str(value).replace("%", "").strip())
        except:
            return None

    return {
        "reach_diff": safe_num(f1.get("reach")) and safe_num(f2.get("reach")) and safe_num(f1.get("reach")) - safe_num(f2.get("reach")),
        "height_diff": safe_num(f1.get("height")) and safe_num(f2.get("height")) and safe_num(f1.get("height")) - safe_num(f2.get("height")),
        "age_diff": safe_num(f1.get("age")) and safe_num(f2.get("age")) and safe_num(f1.get("age")) - safe_num(f2.get("age")),
        "ko_rate_diff": safe_num(f1.get("ko_rate")) and safe_num(f2.get("ko_rate")) and safe_num(f1.get("ko_rate")) - safe_num(f2.get("ko_rate")),
    }
    

# -------------------------------------------------------------
# Build GPT prompt for analysis
# -------------------------------------------------------------
def build_analysis_prompt(matchups: List[Dict[str, str]], odds: Dict[str, Any]) -> str:
    """
    Constructs the message sent to GPT to generate predictions.
    Includes fighter metadata, stats, odds, and computed features.
    """

    blocks = ["You are an MMA fight analyst. Give concise, data-backed predictions.\n"]

    for match in matchups:
        f1 = match["fighter_a"]
        f2 = match["fighter_b"]

        blocks.append(f"Matchup: {f1} vs {f2}")

        odds_data = odds.get(f"{f1}__{f2}", {})

        blocks.append("Odds:")
        blocks.append(str(odds_data))

        blocks.append("Stats:")
        blocks.append(str(match.get("stats_features", {})))

        blocks.append("\nPrediction should include:")
        blocks.append("- Who wins and why")
        blocks.append("- Path to victory")
        blocks.append("- Risk factors")
        blocks.append("- Confidence rating (1–10)")
        blocks.append("- Do NOT hedge. Choose a clear winner.\n")

    return "\n".join(blocks)
