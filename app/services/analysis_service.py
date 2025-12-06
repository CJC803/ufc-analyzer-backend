import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models import Fighter
from app.utils.ufcstats_scraper import fetch_ufcstats_fighter
from app.utils.sherdog_scraper import fetch_sherdog_fighter
from app.utils.tapology_scraper import fetch_tapology_fighter

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
# Helper: Create fighter record
# -------------------------------------------------------
def create_fighter(
    db: Session,
    name: str,
    metadata_json: Dict[str, Any] = None,
    ufcstats_id: str = None,
    sherdog_url: str = None,
    tapology_slug: str = None
) -> Fighter:

    fighter = Fighter(
        name=name.strip(),
        metadata_json=metadata_json or {},
        ufcstats_id=ufcstats_id,
        sherdog_url=sherdog_url,
        tapology_slug=tapology_slug,
    )

    db.add(fighter)
    db.commit()
    db.refresh(fighter)

    logger.info(f"Created new fighter record: {name}")
    return fighter


# -------------------------------------------------------
# Helper: Update fighter record fields
# -------------------------------------------------------
def update_fighter(
    db: Session,
    fighter: Fighter,
    metadata_json: Optional[Dict[str, Any]] = None,
    ufcstats_json: Optional[Dict[str, Any]] = None,
    sherdog_json: Optional[Dict[str, Any]] = None,
    tapology_json: Optional[Dict[str, Any]] = None,
):
    updated = False

    if metadata_json is not None:
        fighter.metadata_json = metadata_json
        updated = True

    if ufcstats_json is not None:
        fighter.ufcstats_json = ufcstats_json
        updated = True

    if sherdog_json is not None:
        fighter.sherdog_json = sherdog_json
        updated = True

    if tapology_json is not None:
        fighter.tapology_json = tapology_json
        updated = True

    if updated:
        db.commit()
        db.refresh(fighter)
        logger.info(f"Updated fighter record: {fighter.name}")

    return fighter


# -------------------------------------------------------
# MAIN SERVICE: Load fighter data (create or update)
# -------------------------------------------------------
def load_fighter_data(db: Session, name: str) -> Fighter:
    """
    Ensures the fighter exists in the DB.
    Scrapes UFCStats / Sherdog / Tapology if needed.
    Merges new scraped data into existing DB record.
    """

    if not name:
        raise ValueError("Fighter name cannot be empty.")

    fighter = get_fighter_by_name(db, name)

    # --------------------------------------------------
    # STEP 1 — Scrape external sources
    # These functions must be safe: return None on fail
    # --------------------------------------------------
    try:
        ufcstats_data = fetch_ufcstats_fighter(name)
    except Exception as e:
        logger.error(f"UFCStats scrape failed for {name}: {e}")
        ufcstats_data = None

    try:
        sherdog_data = fetch_sherdog_fighter(name)
    except Exception as e:
        logger.error(f"Sherdog scrape failed for {name}: {e}")
        sherdog_data = None

    try:
        tapology_data = fetch_tapology_fighter(name)
    except Exception as e:
        logger.error(f"Tapology scrape failed for {name}: {e}")
        tapology_data = None

    # Combine metadata sources
    combined_meta = {
        "ufcstats": ufcstats_data,
        "sherdog": sherdog_data,
        "tapology": tapology_data,
    }

    # --------------------------------------------------
    # STEP 2 — Create or update fighter
    # --------------------------------------------------
    if fighter is None:
        return create_fighter(
            db=db,
            name=name,
            metadata_json=combined_meta,
            ufcstats_id=ufcstats_data.get("id") if ufcstats_data else None,
            sherdog_url=sherdog_data.get("url") if sherdog_data else None,
            tapology_slug=tapology_data.get("slug") if tapology_data else None,
        )

    # UPDATE existing fields
    return update_fighter(
        db=db,
        fighter=fighter,
        metadata_json=combined_meta,
        ufcstats_json=ufcstats_data,
        sherdog_json=sherdog_data,
        tapology_json=tapology_data,
    )
