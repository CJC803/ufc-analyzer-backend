import logging
import json
from typing import Dict, Any, List, Optional

import requests
from sqlalchemy.orm import Session

from app.models import Fighter, Event, Prediction
from app.utils.gpt_safe import gpt_safe_call
from app.services.event_service import extract_json
from app.config import settings

logger = logging.getLogger(__name__)

# --------------------------------------------
# ODDS API CONFIG (The Odds API)
# --------------------------------------------
THE_ODDS_API_KEY = settings.THE_ODDS_API_KEY
ODDS_ENDPOINT = "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"


# ---------------------------------------------------------
# DB: Pull fighter by name
# ---------------------------------------------------------
def _get_fighter(db: Session, name: str) -> Optional[Fighter]:
    if not name:
        return None
    return (
        db.query(Fighter)
        .filter(Fighter.name.ilike(name.strip()))
        .first()
    )


# ---------------------------------------------------------
# DB: Build per-fighter features (stats bundles)
# ---------------------------------------------------------
def compute_stats_features(fighter: Optional[Fighter]) -> Dict[str, Any]:
    """
    Bundle all stored data for a fighter. If missing, return empty shell.
    """
    if not fighter:
        return {
            "metadata": {},
            "ufcstats": {},
            "sherdog": {},
            "tapology": {},
        }

    return {
        "metadata": fighter.metadata_json or {},
        "ufcstats": fighter.ufcstats_json or {},
        "sherdog": fighter.sherdog_json or {},
        "tapology": fighter.tapology_json or {},
    }


# ---------------------------------------------------------
# ODDS: Fetch all current MMA odds once
# ---------------------------------------------------------
def _fetch_all_odds() -> Optional[List[Dict[str, Any]]]:
    """
    Calls The Odds API once and returns the raw event list.
    """
    if not THE_ODDS_API_KEY:
        logger.warning("THE_ODDS_API_KEY not set; skipping odds.")
        return None

    params = {
        "apiKey": THE_ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
    }

    try:
        resp = requests.get(ODDS_ENDPOINT, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        logger.error(f"Odds API request failed: {e}")
        return None


def _find_odds_for_matchup(
    all_odds: Optional[List[Dict[str, Any]]],
    fighter_a: str,
    fighter_b: str,
) -> Optional[Dict[str, Any]]:
    """
    Given the entire odds payload, attempts to find a specific matchup.
    Very fuzzy: just matches fighter names inside outcome names.
    """
    if not all_odds:
        return None

    f1 = fighter_a.lower()
    f2 = fighter_b.lower()

    for event in all_odds:
        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                outcomes = market.get("outcomes", [])
                names = [o["name"].lower() for o in outcomes]

                if f1 in names and f2 in names and len(outcomes) >= 2:
                    # Normalize simple structure
                    return {
                        "source": bookmaker.get("title"),
                        "event_key": event.get("id"),
                        "event_start_time": event.get("commence_time"),
                        "market_key": market.get("key"),
                        "outcomes": outcomes,
                    }

    # No odds found for this fight
    return None


# ---------------------------------------------------------
# Build GPT prompt for full card analysis
# ---------------------------------------------------------
def build_analysis_prompt(
    event: Event,
    enriched_fights: List[Dict[str, Any]]
) -> str:
    """
    `enriched_fights` is a list of:
    {
      "fighter_a_name": str,
      "fighter_b_name": str,
      "fighter_a_features": {...},
      "fighter_b_features": {...},
      "odds": {... or None}
    }
    """

    prompt = f"""
You are an expert MMA analyst and betting strategist.

Analyze the following UFC event and its fights.
Use:
- Technical styles
- Recorded stats (where present)
- Any available odds information

OUTPUT FORMAT:
Return ONLY JSON, no markdown.
Use this EXACT schema:

{{
  "event_name": "",
  "event_date": "",
  "location": "",
  "fights": [
    {{
      "fighter_a": "",
      "fighter_b": "",
      "winner": "",
      "confidence": 0.0,
      "method": "",
      "analysis": "",
      "odds_view": {{
        "has_odds": false,
        "favorite": null,
        "underdog": null,
        "favorite_price": null,
        "underdog_price": null,
        "bookmaker": null
      }}
    }}
  ],
  "parlays": [
    {{
      "legs": [],
      "description": "",
      "risk_profile": ""
    }}
  ]
}}

Rules:
- confidence is a float between 0 and 1.
- method can be a simple outcome like "Decision", "KO/TKO", "Submission".
- odds_view.has_odds must be true if you found usable odds, else false.
- parlays: propose 1–3 parlay ideas based on your fight predictions.
"""

    # We embed the event + enriched fights as JSON context at the end.
    context = {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "location": event.location,
        "fights": enriched_fights,
    }

    prompt += "\n\nCONTEXT:\n"
    prompt += json.dumps(context, indent=2)

    return prompt


# ---------------------------------------------------------
# Run GPT with JSON cleaning
# ---------------------------------------------------------
def _run_gpt_analysis(prompt: str) -> Optional[Dict[str, Any]]:
    raw = gpt_safe_call([prompt])

    clean = extract_json(raw)

    logger.info("======= CLEAN ANALYSIS JSON =======")
    logger.info(clean)
    logger.info("===================================")

    try:
        return json.loads(clean)
    except Exception as e:
        logger.error(f"Failed to parse GPT analysis: {e}")
        return None


# ---------------------------------------------------------
# Save Prediction to DB
# ---------------------------------------------------------
def save_prediction(db: Session, event: Event, data: Dict[str, Any]) -> Prediction:
    prediction = Prediction(
        event_id=event.id,
        analysis_json=data
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


# ---------------------------------------------------------
# MAIN ENTRY: Analyze a single event
# ---------------------------------------------------------
def analyze_event(db: Session, event: Event) -> Optional[Dict[str, Any]]:
    """
    Full pipeline:
    1. Pull fighters from DB
    2. Fetch The Odds API data once
    3. Enrich each fight with stats + odds
    4. Ask GPT for card-wide analysis + parlays
    5. Save to Prediction table
    """

    fight_card = event.fight_card_json or []

    # 1) Fetch odds once
    all_odds = _fetch_all_odds()

    enriched_fights: List[Dict[str, Any]] = []

    for fight in fight_card:
        name_a = fight.get("fighter_a")
        name_b = fight.get("fighter_b")

        fighter_a = _get_fighter(db, name_a) if name_a else None
        fighter_b = _get_fighter(db, name_b) if name_b else None

        a_features = compute_stats_features(fighter_a)
        b_features = compute_stats_features(fighter_b)

        odds = _find_odds_for_matchup(all_odds, name_a or "", name_b or "")

        enriched_fights.append(
            {
                "fighter_a_name": name_a,
                "fighter_b_name": name_b,
                "fighter_a_features": a_features,
                "fighter_b_features": b_features,
                "odds": odds,
            }
        )

    # 2) Build prompt
    prompt = build_analysis_prompt(event, enriched_fights)

    # 3) Run GPT
    analysis = _run_gpt_analysis(prompt)
    if not analysis:
        return None

    # 4) Save prediction to DB
    save_prediction(db, event, analysis)

    return analysis
