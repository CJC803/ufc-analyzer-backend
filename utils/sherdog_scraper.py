import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List

from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(**name**)

SHERDOG_SEARCH = "[https://www.sherdog.com/stats/fightfinder?SearchTxt={query}](https://www.sherdog.com/stats/fightfinder?SearchTxt={query})"

# ---------------------------------------------------------

# Helper: Direct Sherdog search

# ---------------------------------------------------------

def _search_sherdog(name: str) -> Optional[str]:
"""Returns first matching fighter profile URL from Sherdog."""
try:
html = requests.get(SHERDOG_SEARCH.format(query=name.replace(" ", "+")), timeout=10).text
except Exception as e:
logger.error(f"Sherdog search request failed: {e}")
return None

```
soup = BeautifulSoup(html, "html.parser")

# Search results table
results = soup.find("table", class_="fightfinder_result")
if not results:
    return None

rows = results.find_all("tr")
for row in rows:
    link = row.find("a")
    if not link:
        continue

    found_name = link.text.strip().lower()

    if name.lower() in found_name or found_name in name.lower():
        return "https://www.sherdog.com" + link["href"]

return None
```

# ---------------------------------------------------------

# GPT Fallback: Find Sherdog URL

# ---------------------------------------------------------

def _gpt_find_sherdog_url(name: str) -> Optional[str]:
prompt = (
f"Find the Sherdog fighter profile URL for '{name}'. "
f"Return ONLY the full exact URL (starting with https://) or 'null'."
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

# Scrape fighter profile page

# ---------------------------------------------------------

def _scrape_profile(url: str) -> Optional[Dict[str, Any]]:
try:
html = requests.get(url, timeout=10).text
except Exception as e:
logger.error(f"Error fetching Sherdog profile page: {e}")
return None

```
soup = BeautifulSoup(html, "html.parser")

# Fighter name
name_elem = soup.find("span", class_="fn")
name = name_elem.text.strip() if name_elem else "Unknown"

# Nickname
nickname_elem = soup.find("span", class_="nickname")
nickname = nickname_elem.text.strip("“” ") if nickname_elem else None

# Record
record_elem = soup.find("span", class_="record")
record = record_elem.text.strip() if record_elem else None

# Physical attributes + camp
details = {}
info_box = soup.find("div", class_="bio")
if info_box:
    rows = info_box.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            key = cols[0].text.strip().replace(":", "")
            val = cols[1].text.strip()
            details[key] = val

# Fight history
history: List[Dict[str, Any]] = []
table = soup.find("table", class_="fight_history")
if table:
    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header
        cols = row.find_all("td")
        if len(cols) < 7:
            continue

        history.append({
            "result": cols[0].text.strip(),
            "opponent": cols[1].text.strip(),
            "method": cols[3].text.strip(),
            "round": cols[4].text.strip(),
            "time": cols[5].text.strip(),
            "event": cols[6].text.strip(),
        })

return {
    "name": name,
    "nickname": nickname,
    "record": record,
    "details": details,
    "fight_history": history,
    "sherdog_url": url,
}
```

# ---------------------------------------------------------

# Public API

# ---------------------------------------------------------

def get_sherdog_profile(name: str) -> Optional[Dict[str, Any]]:
"""
Full hybrid resolver:
1. Try HTML search
2. If fail, ask GPT for URL
3. Scrape profile page
"""
logger.info(f"Looking up Sherdog profile for: {name}")

```
# Step 1: try direct search
url = _search_sherdog(name)

# Step 2: GPT fallback
if not url:
    logger.warning(f"Sherdog search failed for {name}. Trying GPT fallback...")
    url = _gpt_find_sherdog_url(name)

if not url:
    logger.error(f"No Sherdog URL found for fighter: {name}")
    return None

# Step 3: scrape profile
return _scrape_profile(url)
```
