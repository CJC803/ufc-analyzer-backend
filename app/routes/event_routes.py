from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import load_next_event, get_event_by_name

router = APIRouter(prefix="/events", tags=["Events"])


# ---------------------------------------------------------
# GET — NEXT EVENT
# ---------------------------------------------------------
@router.get("/next")
def events_next(db: Session = Depends(get_db)):
    """
    Fetches the next upcoming UFC event.

    Uses:
    - The Odds API (primary)
    - GPT fallback (secondary)

    Stores event in DB before returning.
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
    Fetch a stored event by name.
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
