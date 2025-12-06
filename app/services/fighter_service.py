import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import Fighter
from app.utils.ufcstats_scraper import get_ufcstats_profile
from app.utils.sherdog_scraper import get_sherdog_profile
from app.utils.tapology_scraper import get_tapology_profile

logger = logging.getLogger(__name__)


# -------------------------------------------------------
# Helper: Get fighter by name (case-insensitive match)
# -------------------------------------------------------
def get_fighter_by_name(db: Session, name: str) -> Optional[Fighter]:
    if not name:
        return None
    return (
        db.query(Fighter)
        .filter(Fighter.name.ilike(name.strip()))
        .first()
    )


# -------------------------------------------------------
# Create fighter record
# -------------------------------------------------------
def create_fighter(
    db: Session,
    name: str,
    metadata_json: Dict[str, Any],
    ufcstats_data: Optional[Dict[str, Any]],
    sherdog_data: Optional[Dict[str, Any]],
    tapology_data: Optional[Dict[str, Any]],
) -> Fighter:

    fighter = Fighter(
        name=name.strip(),

        # Full metadata blob
        metadata_json=metadata_json or {},

        # IDs / URLs
        ufcstats_id=ufcstats_data.get("ufcstats_url") if ufcstats_data else None,
        sherdog_url=sherdog_data.get("sherdog_url") if sherdog_data else None,
        tapology_slug=tapology_data.get("tapology_slug") if tapology_data else None,

        # Stored JSON fields
        ufcstats_json=ufcstats_data,
        sherdog_json=sherdog_data,
        tapology_json=tapology_data,
    )

    db.add(fighter)
    db.commit()
    db.refresh(fighter)

    logger.info(f"Created new fighter record: {name}")
    return fighter


# -------------------------------------------------------
# Update fighter record
# -------------------------------------------------------
def update_fighter(
    db: Session,
    fighter: Fighter,
    metadata_json: Dict[str, Any],
    ufcstats_data: Optional[Dict[str, Any]],
    sherdog_data: Optional[Dict[str, Any]],
    tapology_data: Optional[Dict[str, Any]],
) -> Fighter:

    fighter.metadata_json = metadata_json

    if ufcstats_data:
        fighter.ufcstats_json = ufcstats_data
        fighter.ufcstats_id = ufcstats_data.get("ufcstats_url")

    if sherdog_data:
        fighter.sherdog_json = sherdog_data
        fighter.sherdog_url = sherdog_data.get("sherdog_url")

    if tapology_data:
        fighter.tapology_json = tapology_data
        fighter.tapology_slug = tapology_data.get("tapology_slug")

    db.commit()
    db.refresh(fighter)

    logger.info(f"Updated fighter record: {fighter.name}")
    return fighter


# -------------------------------------------------------
# MAIN SERVICE
# -------------------------------------------------------
def load_fighter_data(db: Session, name: str) -> Fighter:
    """
    Creates or updates a fighter entry with:
    - UFCStats
    - Sherdog
    - Tapology
    """

    fighter = get_fighter_by_name(db, name)

    # Scrapers (all safe)
    try:
        ufcstats_data = get_ufcstats_profile(name)
    except Exception as e:
        logger.error(f"UFCStats failed for {name}: {e}")
        ufcstats_data = None

    try:
        sherdog_data = get_sherdog_profile(name)
    except Exception as e:
        logger.error(f"Sherdog failed for {name}: {e}")
        sherdog_data = None

    try:
        tapology_data = get_tapology_profile(name)
    except Exception as e:
        logger.error(f"Tapology failed for {name}: {e}")
        tapology_data = None

    # Combined metadata
    combined_meta = {
        "ufcstats": ufcstats_data,
        "sherdog": sherdog_data,
        "tapology": tapology_data,
    }

    if fighter is None:
        return create_fighter(
            db=db,
            name=name,
            metadata_json=combined_meta,
            ufcstats_data=ufcstats_data,
            sherdog_data=sherdog_data,
            tapology_data=tapology_data,
        )

    return update_fighter(
        db=db,
        fighter=fighter,
        metadata_json=combined_meta,
        ufcstats_data=ufcstats_data,
        sherdog_data=sherdog_data,
        tapology_data=tapology_data,
    )
