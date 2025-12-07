from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import (
    load_next_event,
    load_all_upcoming_events,
    get_event_by_name
)

router = APIRouter(prefix="/events", tags=["Events"])

# Next event
@router.get("/next")
def api_next_event(db: Session = Depends(get_db)):
    evt = load_next_event(db)
    if not evt:
        raise HTTPException(404, "No upcoming UFC event found.")
    return evt

# All upcoming events
@router.get("/upcoming")
def api_upcoming(db: Session = Depends(get_db)):
    return load_all_upcoming_events(db)

# Event by name
@router.get("/{event_name}")
def api_event_by_name(event_name: str, db: Session = Depends(get_db)):
    evt = get_event_by_name(db, event_name)
    if not evt:
        raise HTTPException(404, f"'{event_name}' not found.")
    return {
        "event_name": evt.event_name,
        "event_date": evt.event_date,
        "location": evt.location,
        "fight_card": evt.fight_card_json or [],
    }
