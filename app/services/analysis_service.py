import logging
import requests
from typing import Dict, Any, Optional

from app.services.fighter_service import load_fighter_data
from app.config import settings
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# --------------------------------------------
# ODDS API CONFIG
# --------------------------------------------
ODDS_API_KEY = settings.THE_ODDS_API_KEY
ODDS_ENDPOINT = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"


# ========================================================
# 1. Fetch betting odds
# ========================================================
def normalize_name(name: str) -> str:
    """Normalize fighter names for matching."""
    return name.lower().replace("-", " ").replace(".", "").strip()


def fetch_fight_odds(f1: str, f2: str) -> Optional[Dict[str, Any]]:
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
    }

    try:
        response = requests.get(ODDS_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        events = response.json()
    except Exception as e:
        logger.error(f"Odds API error: {e}")
        return None

    n1 = normalize_name(f1)
    n2 = normalize_name(f2)

    for event in events:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                outcomes = market.get("outcomes", [])
                names = [normalize_name(o["name"]) for o in outcomes]

                if n1 in names and n2 in names:
                    return {
                        "fighter1": outcomes[0],
                        "fighter2": outcomes[1],
                        "source": bookmaker["title"],
                    }

    return None


# ========================================================
# 2. Extract stats from UFCStats JSON safely
# ========================================================
def compute_stats_features(f1: Dict[str, Any], f2: Dict[str, Any]) -> Dict[str, Any]:

    def safe_float(v):
        try:
            return float(v)
        except:
            return None

    s1 = f1.get("career_stats", {})
    s2 = f2.get("career_stats", {})

    return {
        "sig_strikes_landed_per_min": {
            "fighter1": safe_float(s1.get("SLpM") or s1.get("SLpM:")),
            "fighter2": safe_float(s2.get("SLpM") or s2.get("SLpM:")),
        },
        "sig_strike_accuracy": {
            "fighter1": safe_float(s1.get("Str. Acc.") or s1.get("Str. Acc.:")),
            "fighter2": safe_float(s2.get("Str. Acc.") or s2.get("Str. Acc.:")),
        },
        "takedown_average": {
            "fighter1": safe_float(s1.get("TD Avg.") or s1.get("TD Avg.:")),
            "fighter2": safe_float(s2.get("TD Avg.") or s2.get("TD Avg.:")),
        },
        "takedown_defense": {
            "fighter1": safe_float(s1.get("TD Def.") or s1.get("TD Def.:")),
            "fighter2": safe_float(s2.get("TD Def.") or s2.get("TD Def.:")),
        },
    }


# ========================================================
# 3. Build GPT Analysis Prompt
# ========================================================
def build_analysis_prompt(fighter1, fighter2, stats, odds):
    return f"""
You are an expert MMA analyst.

Break down this matchup with:

1. Strengths vs weaknesses
2. Style matchup details
3. Path to victory for each fighter
4. Predicted winner
5. Confidence score (0–100%)
6. Optional fun parlay suggestion

-------------------
Fighter 1 Data:
{fighter1}

Fighter 2 Data:
{fighter2}

-------------------
Stats Comparison:
{stats}

-------------------
Betting Odds:
{odds}

Give a professional breakdown.
"""


# ========================================================
# 4. MAIN: Analyze a matchup
# ========================================================
def analyze_matchup(db, fighter1_name: str, fighter2_name: str) -> Dict[str, Any]:

    # Load fighters & metadata
    f1_full = load_fighter_data(db, fighter1_name).metadata_json
    f2_full = load_fighter_data(db, fighter2_name).metadata_json

    f1 = f1_full["ufcstats"]
    f2 = f2_full["ufcstats"]

    # Stats
    stats = compute_stats_features(f1, f2)

    # Odds
    odds = fetch_fight_odds(fighter1_name, fighter2_name)

    # Build GPT prompt
    prompt = build_analysis_prompt(f1, f2, stats, odds)

    # GPT analysis
    analysis = gpt_safe_call([{"role": "user", "content": prompt}])

    return {
        "fighter_1": fighter1_name,
        "fighter_2": fighter2_name,
        "stats": stats,
        "odds": odds,
        "analysis_text": analysis,
    }
