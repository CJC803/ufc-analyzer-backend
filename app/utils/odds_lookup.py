import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

from app.schemas import MatchupOdds
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(**name**)

BFO_BASE = "[https://www.bestfightodds.com](https://www.bestfightodds.com)"

# ---------------------------------------------------------

# Helper: Scrape odds for a single event

# ---------------------------------------------------------

def _scrape_event_page(event_name: str) -> Optional[str]:
"""
Searches BestFightOdds homepage for the first event matching event_name.
Returns the full event URL or None.
"""
try:
html = requests.get(BFO_BASE, timeout=10).text
except Exception as e:
logger.error(f"Error loading BestFightOdds homepage: {e}")
return None

```
soup = BeautifulSoup(html, "html.parser")

# Look for events in sidebar
event_links = soup.find_all("a", class_="event-link")
for link in event_links:
    text = link.text.strip().lower()
    if event_name.lower().split()[0] in text:  # match on keyword
        return BFO_BASE + link["href"]

return None
```

# ---------------------------------------------------------

# Helper: Extract matchup odds from event page

# ---------------------------------------------------------

def _scrape_matchups(url: str, matchups: List[Dict[str, str]]) -> List[MatchupOdds]:
"""
Scrape odds for each fight on the event page.
matchups = [{"fighter_a": "...", "fighter_b": "..."}]
"""
logger.info(f"Scraping BFO odds from: {url}")

```
try:
    html = requests.get(url, timeout=10).text
except Exception as e:
    logger.error(f"Error fetching BFO event page: {e}")
    return []

soup = BeautifulSoup(html, "html.parser")

result = []

fight_rows = soup.find_all("tr", class_="fight-row")
for fight in fight_rows:
    fighters = fight.find_all("td", class_="fighter-cell")
    odds_cells = fight.find_all("td", class_="odds-cell")

    if len(fighters) != 2 or len(odds_cells) < 1:
        continue

    f1 = fighters[0].get_text(strip=True)
    f2 = fighters[1].get_text(strip=True)

    # odds-cell contains multiple books; take first book's odds
    odds_text = odds_cells[0].get_text(" ", strip=True).split()
    if len(odds_text) >= 2:
        f1_odds = odds_text[0]
        f2_odds = odds_text[1]
    else:
        f1_odds = None
        f2_odds = None

    # Try to match to our fight list
    for m in matchups:
        a, b = m["fighter_a"], m["fighter_b"]

        if (
            a.lower() in f1.lower() and b.lower() in f2.lower()
        ) or (
            b.lower() in f1.lower() and a.lower() in f2.lower()
        ):
            result.append(
                MatchupOdds(
                    fighter_a=a,
                    fighter_b=b,
                    odds_a=f1_odds,
                    odds_b=f2_odds,
                    book="BFO"
                )
            )
            break

return result
```

# ---------------------------------------------------------

# GPT Fallback

# ---------------------------------------------------------

def _gpt_odds_fallback(matchups: List[Dict[str, str]]):
"""
If BestFightOdds scraping fails, use GPT to retrieve approximate odds.
"""
prompt = (
"Provide CURRENT betting odds for these UFC matchups. "
"Return ONLY JSON like this:\n"
"{ 'odds': [ { 'fighter_a': '', 'fighter_b': '', 'odds_a': '', 'odds_b': '' } ] }\n\n"
f"Matchups:\n{matchups}"
)

```
raw = gpt_safe_call([{"role": "user", "content": prompt}])

try:
    parsed = eval(raw)
    return parsed["odds"]
except Exception:
    logger.error("GPT fallback odds parsing failed.")
    return []
```

# ---------------------------------------------------------

# Public API

# ---------------------------------------------------------

def get_odds_for_matchups(event_name: str, matchups: List[Dict[str, str]]) -> List[MatchupOdds]:
"""
Full pipeline:
1. Find event page on BestFightOdds
2. Scrape odds for matchups
3. GPT fallback if scraping fails or yields incomplete data
"""
logger.info(f"Fetching odds for event: {event_name}")

```
# Step 1 — find event page
event_url = _scrape_event_page(event_name)

if event_url:
    odds = _scrape_matchups(event_url, matchups)
    if odds:
        return odds

logger.warning("Scraping failed or returned no odds. Using GPT fallback.")
gpt_odds = _gpt_odds_fallback(matchups)

# Convert fallback odds to schema
return [
    MatchupOdds(
        fighter_a=o["fighter_a"],
        fighter_b=o["fighter_b"],
        odds_a=o.get("odds_a"),
        odds_b=o.get("odds_b"),
        book="GPT Fallback"
    )
    for o in gpt_odds
]
```
