from typing import List, Optional, Dict, Any
from pydantic import BaseModel

# -------------------------

# Fighter Schemas

# -------------------------

class FighterBase(BaseModel):
name: str

class FighterRead(FighterBase):
id: int
ufcstats_id: Optional[str] = None
sherdog_url: Optional[str] = None
tapology_slug: Optional[str] = None

```
class Config:
    from_attributes = True
```

class FighterMerged(BaseModel):
"""
This is the full 'mega fighter object' returned after merging:
- Metadata
- UFCStats
- Sherdog
- Tapology
- Odds (fight-level, not fighter-level)
"""
name: str
metadata: Optional[Dict[str, Any]] = None
ufcstats: Optional[Dict[str, Any]] = None
sherdog: Optional[Dict[str, Any]] = None
tapology: Optional[Dict[str, Any]] = None

# -------------------------

# Event Schemas

# -------------------------

class FightPair(BaseModel):
fighter_a: str
fighter_b: str
weight_class: Optional[str] = None  # UFCStats often has this

class EventRead(BaseModel):
event_name: str
event_date: Optional[str] = None
location: Optional[str] = None
fight_card: List[FightPair]

# -------------------------

# Odds Schemas

# -------------------------

class MatchupOdds(BaseModel):
fighter_a: str
fighter_b: str
odds_a: Optional[float] = None
odds_b: Optional[float] = None
book: Optional[str] = None

# -------------------------

# Tapology Batch Schema

# -------------------------

class TapologyEntry(BaseModel):
fighter: str
history: Dict[str, Any]  # processed fight history

class TapologyBatchResult(BaseModel):
results: List[TapologyEntry]

# -------------------------

# Merge Result Schema

# -------------------------

class MergedEventData(BaseModel):
event: EventRead
fighters: Dict[str, FighterMerged]
matchups: List[FightPair]
odds: List[MatchupOdds]

# -------------------------

# Analysis Schema

# -------------------------

class AnalysisRequest(BaseModel):
merged_event: MergedEventData

class AnalysisResponse(BaseModel):
raw_text: str
structured: Optional[Dict[str, Any]] = None
