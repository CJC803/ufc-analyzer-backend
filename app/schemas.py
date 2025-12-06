from typing import Optional, List
from pydantic import BaseModel

# -------------------------
# Fight Pair Schema
# -------------------------

class FightPair(BaseModel):
    fighter_a: str
    fighter_b: str
    weight_class: Optional[str] = None

# -------------------------
# Event Read Schema
# -------------------------

class EventRead(BaseModel):
    event_name: str
    event_date: Optional[str] = None
    location: Optional[str] = None
    fight_card: List[FightPair]

# -------------------------
# Prediction Schema
# -------------------------

class PredictionRead(BaseModel):
    id: int
    event_id: int
    analysis_json: dict

    class Config:
        orm_mode = True
