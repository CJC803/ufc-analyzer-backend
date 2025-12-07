import re
import json
import logging
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.models import Fighter, Event, Prediction
from app.utils.gpt_safe import gpt_safe_call
from app.services.odds_service import generate_synthetic_odds


logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# JSON Extractor
# ---------------------------------------------------------
def extract_json(text: str) -> str:
    """Extract JSON object from mixed GPT output."""
    fenced = re.search(r"```json(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    brace = re.search(r"\{.*\}", text, re.DOTALL)
    if brace:
        return brace.group(0).strip()

    return text.strip()


# ---------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------
def _get_fighter(db: Session, name: str) -> Optional[Fighter]:
    if not name:
        return None
    return (
        db.query(Fighter)
        .filter(Fighter.name.ilike(name.strip()))
        .first()
    )


def compute_stats_features(fighter: Optional[Fighter]) -> Dict[str, Any]:
    """Package stored fighter data for GPT."""
    if not fighter:
        return {
            "ufcstats": {},
            "sherdog": {},
            "tapology": {},
            "metadata": {}
        }

    return {
        "ufcstats": fighter.ufcstats_json or {},
        "sherdog": fighter.sherdog_json or {},
        "tapology": fighter.tapology_json or {},
        "metadata": fighter.metadata_json or {},
    }


# ---------------------------------------------------------
# Build GPT Prompt — stats only
# ---------------------------------------------------------
def build_analysis_prompt(event: Event, enriched_fights: List[Dict[str, Any]]) -> str:
    prompt = f"""
You are a world-class MMA analyst.

Use ONLY the structured fighter statistics provided (UFCStats, Sherdog, Tapology).
Do NOT invent records or stats. If data is missing, acknowledge uncertainty.

Your job:
- Compare fighters
- Identify stylistic and statistical advantages
- Predict winner + method + confidence
- Build **1–3 parlay ideas**

OUTPUT FORMAT (JSON ONLY):

{{
  "event_name": "",
  "event_date": "",
  "location": "",
  "fights": [
    {{
      "fighter_a": "",
      "fighter_b": "",
      "analysis": "",
      "winner": "",
      "method": "",
      "confidence": 0.0
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
- confidence = float between 0 and 1
- method = "Decision", "KO/TKO", or "Submission"
"""

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
# GPT Execution
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
# Save prediction to DB
# ---------------------------------------------------------
def save_prediction(db: Session, event: Event, data: Dict[str, Any]) -> Prediction:
    prediction = Prediction(event_id=event.id, analysis_json=data)
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


# ---------------------------------------------------------
# MAIN — Analyze Event Using Stats Only
# ---------------------------------------------------------
def analyze_event(db: Session, event: Event) -> Optional[Dict[str, Any]]:
    """
    Pipeline:
    1. Load fight card
    2. Load fighter stats from DB
    3. Build enriched_fights structure
    4. Feed stats → GPT for analysis + parlay suggestions
    5. Save to predictions table
    """

    fight_card = event.fight_card_json or []
    enriched_fights = []

    for fight in fight_card:
        name_a = fight.get("fighter_a")
        name_b = fight.get("fighter_b")

        fighter_a = _get_fighter(db, name_a)
        fighter_b = _get_fighter(db, name_b)

        enriched_fights.append(
            {
                "fighter_a_name": name_a,
                "fighter_b_name": name_b,
                "fighter_a_features": compute_stats_features(fighter_a),
                "fighter_b_features": compute_stats_features(fighter_b),
            }
        )

    prompt = build_analysis_prompt(event, enriched_fights)
    analysis = _run_gpt_analysis(prompt)

    if not analysis:
        return None

    save_prediction(db, event, analysis)
    return analysis
