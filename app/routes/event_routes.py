from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import (
    load_next_event,
)
from app.services.analysis_service import analyze_event

router = APIRouter(prefix="/events", tags=["Events"])

@router.get("/next")
def api_next_event(db: Session = Depends(get_db)):
    evt = load_next_event(db)
    if not evt:
        raise HTTPException(404, "No upcoming event found.")
    return evt

@router.get("/upcoming")
def api_upcoming(db: Session = Depends(get_db)):
    return load_all_upcoming_events(db)

@router.get("/analyze-next")
def api_analyze_next_event(db: Session = Depends(get_db)):
    evt = load_next_event(db)
    if not evt:
        raise HTTPException(404, "No upcoming event.")
    return analyze_event(evt)

@router.get("/{event_name}")
def api_event_by_name(event_name: str, db: Session = Depends(get_db)):
    evt = get_event_by_name(db, event_name)
    if not evt:
        raise HTTPException(404, f"Event '{event_name}' not found.")
    return {
        "event_name": evt.event_name,
        "event_date": evt.event_date,
        "location": evt.location,
        "fight_card": evt.fight_card_json
    }
