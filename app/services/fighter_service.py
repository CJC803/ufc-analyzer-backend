import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Fighter
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Helper: Get or create fighter by name
# ---------------------------------------------------------

def _get_or_create_fighter(db: Session, name: str) -> Fighter:
    fighter = (
        db.query(Fighter)
        .filter(Fighter.name.ilike(name))
        .first()
    )

    if fighter:
        return fighter

    fighter = Fighter(name=name)
    db.add(fighter)
    db.commit()
    db.refresh(fighter)
    return fighter

# ---------------------------------------------------------
# Public: Load fighter data via GPT
# ---------------------------------------------------------

def load_fighter_data(db: Session, name: str) -> Dict[str, Any]:
    """
    Ask GPT for structured fighter metadata.
    """

    prompt = (
        f"Give me structured fighter metadata for '{name}' "
        "in JSON format:\n"
        "{"
        "  'age': int or null,"
        "  'height': str or null,"
        "  'reach': str or null,"
        "  'style': str or null,"
        "  'record': str or null"
        "}"
    )

    raw = gpt_safe_call([prompt])

    try:
        data = eval(raw)  # Expect GPT to return a JSON-like dict
    except Exception:
        logger.error("GPT returned invalid fighter JSON.")
        data = {}

    fighter = _get_or_create_fighter(db, name)
    fighter.metadata_json = data
    db.commit()

    return data
