import logging
import requests
from typing import Dict, Any, Optional, List

from app.services.fighter_service import load_fighter_data
from app.config import settings
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# --------------------------------------------
# ODDS API CONFIG  (Option B you selected)
# --------------------------------------------
ODDS_API_KEY = settings.ODDS_API_KEY
ODDS_ENDPOINT = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"


# ========================================================
# 1. Fetch Betting Odds
# ========================================================
def fetch_fight_odds(fighter1: str, fighter2: str) -> Optional[Dict[str, Any]]:
    """
    Fetches odds for a specific matchup using Option B provider.
    Returns normalized moneyline odds for both fighters.
    """

    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
    }

    try:
        response = requests.get(ODDS_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

    except Exception as e:
        logger.error(f"Odds API request failed: {e}")
        return None

    # Find matching fight
    fighter1_lower = fighter1.lower()
    fighter2_lower = fighter2.lower()

    for event in data:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                outcomes = market.get("outcomes", [])

                names = [o["name"].lower() for o in outcomes]

                if fighter1_lower in names and fighter2_lower in names:
                    return {
                        "fighter1": outcomes[0],
                        "fighter2": outcomes[1],
                        "source": bookmaker["title"],
                    }

    return None


# ========================================================
# 2. Compute useful stats features
# ========================================================
def compute_stats_features(f1: Dict[str, Any], f2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts comparable numerical features from UFCStats fighter profiles.
    Very expandable — safe if data missing.
    """

    def parse_float(v):
        try:
            return float(v)
        except:
            return None

    f1_stats = f1.get("career_stats", {})
    f2_stats = f2.get("career_stats", {})

    return {
        "sig_str_land_per_min": {
            "fighter1": parse_float(f1_stats.get("SLpM")),
            "fighter2": parse_float(f2_stats.get("SLpM")),
        },
        "sig_str_acc": {
            "fighter1": parse_float(f1_stats.get("Str. Acc.")),
            "fighter2": parse_float(f2_stats.get("Str. Acc.")),
        },
        "takedown_avg": {
            "fighter1": parse_float(f1_stats.get("TD Avg.")),
            "fighter2": parse_float(f2_stats.get("TD Avg.")),
        },
        "takedown_def": {
            "fighter1": parse_float(f1_stats.get("TD Def.")),
            "fighter2": parse_float(f2_stats.get("TD Def.")),
        },
    }


# ========================================================
# 3. Build Fight Analysis Prompt
# ========================================================
def build_analysis_prompt(
    fighter1: Dict[str, Any],
    fighter2: Dict[str, Any],
    stats: Dict[str, Any],
    odds: Optional[Dict[str, Any]]
) -> str:

    return f"""
You are an MMA fight analyst.

Compare the following two fighters and produce:

1. Breakdown of strengths & weaknesses
2. Style vs style analysis
3. Path to victory for each fighter
4. Predicted winner
5. Confidence level (0–100%)
6. Optional parlay suggestion based on the analysis

-------------------
Fighter 1:
{fighter1}

Fighter 2:
{fighter2}

-------------------
Stats Comparison:
{stats}

-------------------
Betting Odds:
{odds}

Give a professional, detailed breakdown.
"""


# ========================================================
# 4. Main function: analyze a matchup
# ========================================================
def analyze_matchup(db, fighter1_name: str, fighter2_name: str) -> Dict[str, Any]:
    """
    Loads both fighters → scrapes data → pulls odds → computes stats → GPT analysis.
    """

    # Load fighter records & scrape if needed
    f1 = load_fighter_data(db, fighter1_name).metadata_json["ufcstats"]
    f2 = load_fighter_data(db, fighter2_name).metadata_json["ufcstats"]

    # Compute stats features
    stats = compute_stats_features(f1, f2)

    # Get bookmaker odds
    odds = fetch_fight_odds(fighter1_name, fighter2_name)

    # Build GPT prompt
    prompt = build_analysis_prompt(f1, f2, stats, odds)

    # Run safe GPT
    result = gpt_safe_call([
        {"role": "user", "content": prompt}
    ])

    return {
        "fighter_1": fighter1_name,
        "fighter_2": fighter2_name,
        "stats": stats,
        "odds": odds,
        "analysis_text": result,
    }
