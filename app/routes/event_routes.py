from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.event_service import load_next_event, get_event_by_name

router = APIRouter(prefix="/events", tags=["Events"])


# ------------------------------------------------------
# GET /events/next
# ------------------------------------------------------
@router.get("/next")
def events_next(db: Session = Depends(get_db)):
    """
    Returns the next UFC event:
    {
      "event_name": "...",
      "event_date": "...",
      "location": "...",
      "fight_card": [...]
    }
    """
    event_json = load_next_event(db)

    if not event_json:
        return {
            "event_name": None,
            "event_date": None,
            "location": None,
            "fight_card": []
        }

    return event_json


# ------------------------------------------------------
# GET /events/{name}
# ------------------------------------------------------
@router.get("/{name}")
def events_by_name(name: str, db: Session = Depends(get_db)):
    """
    Fetch a saved event by name.
    """
    event = get_event_by_name(db, name)
    if not event:
        return {"error": "Event not found"}

    return {
        "event_name": event.event_name,
        "event_date": event.event_date,
        "location": event.location,
        "fight_card": event.fight_card_json or []
    }
