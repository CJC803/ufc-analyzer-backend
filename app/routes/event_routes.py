from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import load_next_event, get_event_by_name
from app.services.analysis_service import analyze_event

router = APIRouter(prefix="/events", tags=["Events"])


# ---------------------------------------------------------
# GET — NEXT EVENT (Odds API -> GPT fallback -> store + return)
# ---------------------------------------------------------
@router.get("/next")
def events_next(db: Session = Depends(get_db)):
    """
    Fetches the next upcoming UFC event using:
    - The Odds API (primary)
    - GPT fallback (secondary)
    
    Stores event in DB before returning it.
    """
    event_json = load_next_event(db)

    if not event_json:
        raise HTTPException(
            status_code=404,
            detail="No upcoming UFC event could be determined."
        )

    return event_json


# ---------------------------------------------------------
# GET — EVENT BY NAME
# ---------------------------------------------------------
@router.get("/{event_name}")
def event_by_name(event_name: str, db: Session = Depends(get_db)):
    """
    Retrieve a stored event from DB by its exact name.
    """
    event = get_event_by_name(db, event_name)

    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_name}' not found."
        )

    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "location": event.location,
        "fight_card": event.fight_card_json or [],
    }


# ---------------------------------------------------------
# POST — ANALYZE EVENT (GPT + Fighter Stats + Odds API)
# ---------------------------------------------------------
@router.post("/{event_name}/analyze")
def analyze_event_by_name(event_name: str, db: Session = Depends(get_db)):
    """
    Run a full analysis on a stored event:

    - Pull fighter stats from DB
    - Pull betting odds from The Odds API
    - Generate predictions & parlays with GPT
    - Save into Prediction table
    - Return prediction JSON
    """
    event = get_event_by_name(db, event_name)

    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event '{event_name}' not found."
        )

    result = analyze_event(db, event)

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze event."
        )

    return result
