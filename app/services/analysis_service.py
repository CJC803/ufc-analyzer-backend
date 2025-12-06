import logging
from typing import Dict, Any, List
from app.utils.openai_client import run_stream

logger = logging.getLogger(**name**)

# ---------------------------------------------------------

# Lightweight statistical scoring

# ---------------------------------------------------------

def compute_stats_features(fighter: Dict[str, Any]) -> Dict[str, float]:
"""
Computes basic metrics from UFCStats + fight history.
Returns dict of numeric features usable in GPT analysis.
"""

```
stats = fighter.get("career_stats", {})
fh = fighter.get("fight_history", {}).get("tapology", [])

# --- Striking metrics ---
slpm = float(stats.get("SLpM", 0) or 0)
sapm = float(stats.get("SApM", 0) or 0)
striking_diff = slpm - sapm

# --- Grappling metrics ---
tda = float(stats.get("TDAvg", 0) or 0)
tdf = float(stats.get("TDDef", 0) or 0)

# --- Finish rate ---
wins = sum(1 for f in fh if f.get("result") == "Win")
losses = sum(1 for f in fh if f.get("result") == "Loss")
finishes = sum(
    1
    for f in fh
    if f.get("method", "").lower() in ["ko", "tko", "submission", "sub"]
)
finish_rate = finishes / wins if wins > 0 else 0

# --- Experience score ---
total_fights = len(fh)
experience = total_fights / 20  # normalized (20 fights = 1.0)

# --- Momentum score (last 5 fights) ---
recent = fh[:5]
if recent:
    wins_recent = sum(1 for f in recent if f.get("result") == "Win")
    momentum = wins_recent / len(recent)
else:
    momentum = 0.5  # neutral baseline

return {
    "striking_diff": striking_diff,
    "takedown_avg": tda,
    "takedown_def": tdf,
    "finish_rate": finish_rate,
    "experience": experience,
    "momentum": momentum,
}
```

# ---------------------------------------------------------

# Build GPT prompt

# ---------------------------------------------------------

def build_analysis_prompt(matchup_bundle: Dict[str, Any]) -> List[Dict[str, str]]:
"""
Builds the system + user messages for GPT streaming analysis.
Input format: {
"event_name": "",
"fighter_a": {merged fighter object},
"fighter_b": {merged fighter object},
"odds": {odds_a, odds_b},
"a_features": {computed features},
"b_features": {computed features}
}
"""

```
a = matchup_bundle["fighter_a"]
b = matchup_bundle["fighter_b"]

af = matchup_bundle["a_features"]
bf = matchup_bundle["b_features"]
odds = matchup_bundle["odds"]

user_prompt = f"""
```

You are an MMA analysis engine. Use *both* the statistical metrics and the
fighter summaries to produce a hybrid analysis.

Provide:

1. A detailed but concise technical analysis (striking, grappling, cardio, momentum).
2. A prediction (winner + method + confidence %).
3. A short justification referencing stats + style matchups.
4. Consider the odds and identify if value exists.

--- EVENT: {matchup_bundle['event_name']} ---

### Fighter A: {a['name']}

Record: {a.get('record')}
Height: {a.get('height')}
Reach: {a.get('reach')}
Style Summary: {a.get('style_summary')}

Stats:

* Striking differential: {af['striking_diff']}
* Takedown avg: {af['takedown_avg']}
* Takedown defense: {af['takedown_def']}
* Finish rate: {af['finish_rate']}
* Experience score: {af['experience']}
* Momentum: {af['momentum']}

### Fighter B: {b['name']}

Record: {b.get('record')}
Height: {b.get('height')}
Reach: {b.get('reach']}
Style Summary: {b.get('style_summary')}

Stats:

* Striking differential: {bf['striking_diff']}
* Takedown avg: {bf['takedown_avg']}
* Takedown defense: {bf['takedown_def']}
* Finish rate: {bf['finish_rate']}
* Experience score: {bf['experience']}
* Momentum: {bf['momentum']}

### ODDS

{a['name']}: {odds.odds_a}
{b['name']}: {odds.odds_b}

### FORMAT (STRICT):

Return JSON:
{
"analysis": "...",
"prediction": {
"winner": "",
"method": "",
"confidence": 0.0
},
"value_notes": ""
}
"""

```
return [
    {"role": "system", "content": "You are a professional MMA analyst and data modeler."},
    {"role": "user", "content": user_prompt},
]
```

# ---------------------------------------------------------

# Streaming analysis

# ---------------------------------------------------------

def stream_fight_analysis(matchup_bundle: Dict[str, Any]):
"""
Runs GPT streaming analysis. The caller (FastAPI) will stream each token to Streamlit.
"""
messages = build_analysis_prompt(matchup_bundle)
return run_stream(messages, model="gpt-4o-mini", temperature=0.2)
