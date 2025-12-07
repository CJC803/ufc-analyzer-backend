from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Event
from app.services.analysis_service import analyze_event

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.get("/{event_id}")
def run_analysis(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    result = analyze_event(db, event)

    if not result:
        raise HTTPException(status_code=500, detail="Failed to generate analysis")

    return result
