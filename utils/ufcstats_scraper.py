import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any

from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(**name**)

UFC_SEARCH = "[http://ufcstats.com/statistics/fighters?query={query}&page=all](http://ufcstats.com/statistics/fighters?query={query}&page=all)"
UFC_BASE = "[http://ufcstats.com](http://ufcstats.com)"

# ---------------------------------------------------------

# Helper: Find fighter URL via search page

# ---------------------------------------------------------

def _find_fighter_url(name: str) -> Optional[str]:
"""
Scrapes UFCStats search results to find the fighter's detail page URL.
"""
try:
html = requests.get(UFC_SEARCH.format(query=name.replace(" ", "+")), timeout=10).text
except Exception as e:
logger.error(f"UFCStats search request failed: {e}")
return None

```
soup = BeautifulSoup(html, "html.parser")
table = soup.find("table", class_="b-statistics__table")

if not table:
    return None

rows = table.find_all("tr")[1:]  # skip header
for row in rows:
    cols = row.find_all("td")
    if not cols:
        continue

    link = cols[0].find("a")
    if not link:
        continue

    found_name = link.text.strip().lower()

    if name.lower() in found_name or found_name in name.lower():
        return link["href"]

# No matches
return None
```

# ---------------------------------------------------------

# GPT Fallback: Ask for UFCStats ID or corrected name

# ---------------------------------------------------------

def _gpt_find_ufcstats_id(name: str) -> Optional[str]:
prompt = (
f"Find the UFCStats.com fighter URL for '{name}'. "
f"Return ONLY the full URL OR 'null' if unknown."
)

```
raw = gpt_safe_call([{"role": "user", "content": prompt}])

raw = raw.strip()
if raw.lower() == "null":
    return None

if raw.startswith("http"):
    return raw

return None
```

# ---------------------------------------------------------

# Scrape fighter page

# ---------------------------------------------------------

def _scrape_fighter_page(url: str) -> Optional[Dict[str, Any]]:
"""
Scrapes the UFCStats fighter page for:
- basic info
- physical stats
- career statistics
- fight history
"""
try:
html = requests.get(url, timeout=10).text
except Exception as e:
logger.error(f"Error fetching fighter page: {e}")
return None

```
soup = BeautifulSoup(html, "html.parser")

# Fighter name
name_elem = soup.find("span", class_="b-content__title-highlight")
name = name_elem.text.strip() if name_elem else "Unknown"

# Physical attributes
attr_map = {}
left_col = soup.find_all("li", class_="b-list__box-list-item")
for item in left_col:
    text = item.get_text(" ", strip=True)
    if ":" in text:
        key, value = text.split(":", 1)
        attr_map[key.strip()] = value.strip()

# Career stats table
stats_map = {}
stats_table = soup.find("div", class_="b-list__info-box b-list__info-box_style_small-width")
if stats_table:
    rows = stats_table.find_all("li", class_="b-list__box-list-item")
    for row in rows:
        text = row.get_text(" ", strip=True)
        if ":" in text:
            key, value = text.split(":", 1)
            stats_map[key.strip()] = value.strip()

# Fight history
fights = []
history = soup.find("table", class_="b-fight-details__table")
if history:
    for row in history.find_all("tr", class_="b-fight-details__table-row"):
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        fights.append({
            "result": cols[0].text.strip(),
            "opponent": cols[1].text.strip(),
            "method": cols[2].text.strip(),
            "round": cols[3].text.strip(),
            "time": cols[4].text.strip(),
            "event": cols[6].text.strip(),
        })

return {
    "name": name,
    "attributes": attr_map,
    "career_stats": stats_map,
    "fight_history": fights,
    "ufcstats_url": url,
}
```

# ---------------------------------------------------------

# Public API

# ---------------------------------------------------------

def get_ufcstats_profile(name: str) -> Optional[Dict[str, Any]]:
"""
Full hybrid strategy:
1. Try direct UFCStats search
2. If nothing found → GPT fallback for fighter URL
3. Scrape fighter page from UFCStats
"""
logger.info(f"Looking up UFCStats profile for: {name}")

```
# Step 1: Try scraping search
url = _find_fighter_url(name)

# Step 2: If failed, try GPT for corrected URL
if not url:
    logger.warning(f"No UFCStats search result for {name}. Trying GPT fallback...")
    url = _gpt_find_ufcstats_id(name)

# Step 3: If still nothing → give up
if not url:
    logger.error(f"Could not find UFCStats URL for fighter: {name}")
    return None

# Step 4: Scrape fighter page
return _scrape_fighter_page(url)
```
