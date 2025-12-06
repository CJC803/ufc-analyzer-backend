import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------

# Helper: field normalization utilities

# ---------------------------------------------------------

def _pick_best(*values):
"""Return the first non-null, non-empty value."""
for v in values:
if v not in (None, "", "N/A", "-", {}):
return v
return None

def _clean_name(name: Optional[str]) -> Optional[str]:
if not name:
return None
return name.replace("\xa0", " ").strip()

def _normalize_record(record: Optional[str]) -> Optional[str]:
"""
Sherdog format: "20-5-0"
UFCStats format varies; best to keep Sherdog if available.
"""
if not record:
return None
return record.strip()

def _parse_height(value: str) -> Optional[str]:
"""Normalize height: keep original style for now, model can parse later."""
if not value:
return None
return value.replace(" ", "").strip()

def _parse_reach(value: str) -> Optional[str]:
"""Normalize reach (inches)."""
if not value:
return None
return value.strip()

# ---------------------------------------------------------

# Main merge function

# ---------------------------------------------------------

def merge_fighter_data(
name: str,
metadata: Optional[Dict[str, Any]] = None,
ufcstats: Optional[Dict[str, Any]] = None,
sherdog: Optional[Dict[str, Any]] = None,
tapology: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
"""
Smart merging strategy:
Priority order for core identity fields:
UFCStats > Sherdog > Metadata > Tapology > raw name
"""
logger.info(f"Merging fighter data for: {name}")

```
merged = {}

# --------------------------
# Basic identity fields
# --------------------------
merged["name"] = _clean_name(
    _pick_best(
        ufcstats.get("name") if ufcstats else None,
        sherdog.get("name") if sherdog else None,
        metadata.get("name") if metadata else None,
        name,
    )
)

merged["nickname"] = _pick_best(
    sherdog.get("nickname") if sherdog else None,
    metadata.get("nickname") if metadata else None
)

merged["record"] = _normalize_record(
    _pick_best(
        sherdog.get("record") if sherdog else None,
        ufcstats.get("career_stats", {}).get("Record") if ufcstats else None
    )
)

# --------------------------
# Physical attributes
# --------------------------
# UFCStats is usually the best for these
attrs = ufcstats.get("attributes", {}) if ufcstats else {}
sd_details = sherdog.get("details", {}) if sherdog else {}

merged["height"] = _pick_best(
    attrs.get("Height"),
    sd_details.get("Height")
)

merged["reach"] = _pick_best(
    attrs.get("Reach"),
    sd_details.get("Reach")
)

merged["stance"] = _pick_best(
    attrs.get("Stance"),
    metadata.get("stance") if metadata else None
)

merged["dob"] = _pick_best(
    attrs.get("DOB"),
    sd_details.get("Birth Date")
)

# --------------------------
# Stats and fight history
# --------------------------
merged["career_stats"] = ufcstats.get("career_stats", {}) if ufcstats else {}

merged["fight_history"] = {
    "ufcstats": ufcstats.get("fight_history") if ufcstats else [],
    "sherdog": sherdog.get("fight_history") if sherdog else [],
    "tapology": tapology.get("history") if tapology else []
}

# --------------------------
# Style summary (GPT-generated Tapology summary)
# --------------------------
merged["style_summary"] = tapology.get("summary") if tapology else None

# --------------------------
# Source URLs
# --------------------------
merged["sources"] = {
    "ufcstats": ufcstats.get("ufcstats_url") if ufcstats else None,
    "sherdog": sherdog.get("sherdog_url") if sherdog else None
}

return merged
```
