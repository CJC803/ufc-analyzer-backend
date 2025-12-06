from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import load_next_event, get_event_by_name

router = APIRouter(prefix="/events")

@router.get("/")
def list_events():
    return {
        "endpoints": [
            "/events/next",
            "/events/{event_name}"
        ]
    }

@router.get("/next")
def events_next(db: Session = Depends(get_db)):
    return load_next_event(db)

@router.get("/{event_name}")
def events_by_name(event_name: str, db: Session = Depends(get_db)):
    return get_event_by_name(db, event_name)
