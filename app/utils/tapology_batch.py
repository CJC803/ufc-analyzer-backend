import logging
from typing import List, Dict, Any

from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

TAPOLOGY_PROMPT_TEMPLATE = """
You are an assistant extracting Tapology-style fighter profiles.

For EACH fighter in this list, return:

* A short summary of their fighting style, career trajectory, strengths/weaknesses.
* A structured 'iHistory' style JSON fight history.

Fighters:
{fighters}

RESPONSE FORMAT (STRICT JSON):
{
"results": [
{
"fighter": "Name",
"summary": "Short summary text",
"history": [
{
"opponent": "Name",
"result": "Win/Loss",
"method": "KO/TKO/Sub/Decision/etc",
"round": "1/2/3/5",
"time": "4:13",
"event": "Event Name",
"date": "YYYY-MM-DD"
}
]
}
]
}
Ensure this is valid JSON parsable by Python. No additional commentary.
"""

def get_tapology_batch(fighters: List[str]) -> Dict[str, Any]:
"""
Sends a list of fighters (up to 20) to GPT and retrieves Tapology-style summaries
+ structured histories.
"""

```
if len(fighters) > 20:
    raise ValueError("Tapology batch limit is 20 fighters per request.")

logger.info(f"Running Tapology GPT batch for {len(fighters)} fighters")

prompt = TAPOLOGY_PROMPT_TEMPLATE.format(
    fighters="\n".join(f"- {f}" for f in fighters)
)

raw = gpt_safe_call([{"role": "user", "content": prompt}], model="gpt-4o-mini")

# GPT yields JSON-like string → parse with eval (safe due to strict formatting)
try:
    parsed = eval(raw)
except Exception as e:
    logger.error("Failed to parse GPT Tapology batch JSON.", e)
    raise RuntimeError("Invalid JSON returned by GPT Tapology batch.")

# Convert into a dictionary for easier merging later
result_map = {}
for entry in parsed.get("results", []):
    name = entry["fighter"]
    result_map[name] = {
        "summary": entry.get("summary"),
        "history": entry.get("history", [])
    }

return result_map
```
