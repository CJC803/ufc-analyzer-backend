import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import Fighter
from app.utils.ufcstats_scraper import get_ufcstats_profile
from app.utils.sherdog_scraper import get_sherdog_profile
from app.utils.fighter_merge import merge_fighter_data

logger = logging.getLogger(__name__)

# ---------------------------------------------------------

# DB Helper

# ---------------------------------------------------------

def _get_or_create(db: Session, name: str) -> Fighter:
fighter = db.query(Fighter).filter(Fighter.name.ilike(name)).first()
if fighter:
return fighter

```
fighter = Fighter(name=name)
db.add(fighter)
db.commit()
db.refresh(fighter)
return fighter
```

# ---------------------------------------------------------

# Main: Fetch & Cache Fighter Data

# ---------------------------------------------------------

def load_fighter_data(
db: Session,
name: str,
tapology_map: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
"""
Loads fighter data with aggressive caching:
- If DB already has a data source, skip scraper for that source.
- Else call scraper/GPT and update DB.
- tapology_map comes from tapology_batch for multiple fighters at once.
"""

```
fighter = _get_or_create(db, name)

# -------------------------
# UFCStats
# -------------------------
if fighter.ufcstats_json:
    ufcstats_data = fighter.ufcstats_json
else:
    ufcstats_data = get_ufcstats_profile(name)
    if ufcstats_data:
        fighter.ufcstats_json = ufcstats_data
        # attempt to store ID if available
        if "ufcstats_url" in ufcstats_data:
            fighter.ufcstats_id = ufcstats_data["ufcstats_url"].split("/")[-1]
        db.commit()

# -------------------------
# Sherdog
# -------------------------
if fighter.sherdog_json:
    sherdog_data = fighter.sherdog_json
else:
    sherdog_data = get_sherdog_profile(name)
    if sherdog_data:
        fighter.sherdog_json = sherdog_data
        if "sherdog_url" in sherdog_data:
            fighter.sherdog_url = sherdog_data["sherdog_url"]
        db.commit()

# -------------------------
# Tapology (from batch results)
# -------------------------
if fighter.tapology_json:
    tapology_data = fighter.tapology_json
else:
    if tapology_map and name in tapology_map:
        tapology_data = tapology_map[name]
        fighter.tapology_json = tapology_data
        db.commit()
    else:
        tapology_data = None

# -------------------------
# Metadata (optional expansion later)
# -------------------------
meta = fighter.metadata_json or {}

# -------------------------
# Merge everything
# -------------------------
merged = merge_fighter_data(
    name=name,
    metadata=meta,
    ufcstats=ufcstats_data,
    sherdog=sherdog_data,
    tapology=tapology_data
)

return merged
```
