import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from app.routes.event_routes import router as events_router
from app.database import get_db
from app.services.event_service import load_next_event, get_event_by_name
from app.services.fighter_service import load_fighter_data
from app.services.analysis_service import compute_stats_features, build_analysis_prompt
from app.services.odds_service import get_odds_for_matchups  # MAKE SURE THIS FILE NAME MATCHES YOUR IMPLEMENTATION
from app.utils.tapology_batch import get_tapology_batch
from app.utils.openai_client import run, run_stream

app = FastAPI(title="UFC Analyzer Backend", version="2.0")


# --------------------------------------------------------------
# CORS (allow Streamlit frontend)
# --------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(events_router)

# --------------------------------------------------------------
# ROOT
# --------------------------------------------------------------

@app.get("/")
def root():
    return {"status": "ok", "message": "UFC Analyzer Backend Running"}


# --------------------------------------------------------------
# 1. NEXT EVENT
# --------------------------------------------------------------

@app.get("/next_event")
def next_event(db: Session = Depends(get_db)):
    """
    Scrape + cache the next UFC event.
    """
    event_json = load_next_event(db)
    return event_json


# --------------------------------------------------------------
# 2. LOAD FIGHTERS (batch)
# --------------------------------------------------------------

@app.post("/load_fighters")
def load_fighters(payload: dict, db: Session = Depends(get_db)):
    """
    Input:
    {
        "fighters": ["A", "B", "C"],
        "tapology": { "A": {...}, "B": {...} }   # optional
    }
    """
    fighters = payload.get("fighters", [])
    tapology_map = payload.get("tapology", {})

    merged_profiles = {}

    for name in fighters:
        merged = load_fighter_data(db, name, tapology_map=tapology_map)
        merged_profiles[name] = merged

    return {"fighters": merged_profiles}


# --------------------------------------------------------------
# 3. ODDS LOOKUP
# --------------------------------------------------------------

@app.post("/odds")
def odds_lookup(payload: dict):
    """
    Input:
    {
        "event_name": "",
        "matchups": [
            {"fighter_a": "A", "fighter_b": "B"},
            ...
        ]
    }
    """
    event_name = payload["event_name"]
    matchups = payload["matchups"]

    odds = get_odds_for_matchups(event_name, matchups)

    return {"odds": [o.dict() for o in odds]}


# --------------------------------------------------------------
# 4. STREAMING SINGLE-FIGHT ANALYSIS
# --------------------------------------------------------------

@app.post("/analysis/stream")
def streaming_analysis(payload: dict):
    """
    Input:
    {
        "matchup_bundle": { ... }
    }
    """
    bundle = payload["matchup_bundle"]
    stream = run_stream(build_analysis_prompt(bundle))

    # FastAPI streaming response via generator
    def token_stream():
        for token in stream:
            yield token

    return token_stream()


# --------------------------------------------------------------
# INTERNAL: NON-STREAMING ANALYSIS (USED BY FULL EVENT)
# --------------------------------------------------------------

def run_full_analysis_nonstream(bundle: dict) -> dict:
    """
    Runs the analysis prompt (non-streaming) to get JSON prediction.
    """
    messages = build_analysis_prompt(bundle)
    raw = run(messages, model="gpt-4o-mini", temperature=0.2)

    # Parse JSON from GPT response
    try:
        parsed = eval(raw)
    except Exception:
        parsed = {
            "analysis": raw,
            "prediction": {
                "winner": None,
                "method": None,
                "confidence": 0.0
            },
            "value_notes": ""
        }

    return parsed


# --------------------------------------------------------------
# 5. HYBRID PARLAY BUILDER
# --------------------------------------------------------------

def build_parlays(predictions: list) -> list:
    """
    Hybrid parlay logic:
    1. Select strong favorites (confidence > 0.65)
    2. Select one underdog with value (confidence > 0.45 AND positive odds)
    3. GPT formats the final parlays
    """
    strong = [p for p in predictions if p["prediction"]["confidence"] >= 0.65]
    value = [p for p in predictions if p["prediction"]["confidence"] >= 0.45 and p["odds"]["odds_b"].startswith("+")]

    legs = [x["prediction"]["winner"] for x in strong][:2]  # top 2 confident legs
    val_leg = value[0]["prediction"]["winner"] if value else None

    parlay_data = {
        "strong_legs": legs,
        "value_leg": val_leg
    }

    # Format with GPT
    messages = [
        {"role": "system", "content": "You generate parlay explanations for MMA events."},
        {"role": "user", "content": f"Formulate parlays based on this: {parlay_data}. Return JSON with keys 'parlays'."}
    ]

    raw = run(messages, model="gpt-4o-mini", temperature=0.2)

    try:
        parsed = eval(raw)
        return parsed.get("parlays", [])
    except Exception:
        return []


# --------------------------------------------------------------
# 6. FULL EVENT ANALYSIS
# --------------------------------------------------------------

@app.get("/full_event_analysis")
def full_event_analysis(db: Session = Depends(get_db)):
    """
    Runs the entire pipeline as ONE endpoint:
    - Load event
    - Tapology batch
    - Fighter merge + load
    - Odds
    - Full per-fight analysis (non-streaming)
    - Hybrid parlay builder
    """

    # STEP 1: Load event
    event = load_next_event(db)
    event_name = event["event_name"]

    # STEP 2: collect fighter names from card
    names = []
    for f in event["fight_card"]:
        names.append(f["fighter_a"])
        names.append(f["fighter_b"])

    names = list(set(names))

    # STEP 3: Tapology batch
    tapo = get_tapology_batch(names)

    # STEP 4: Load fighters
    fighters = {}
    for n in names:
        fighters[n] = load_fighter_data(db, n, tapology_map=tapo)

    # STEP 5: Odds
    card_matchups = [{"fighter_a": f["fighter_a"], "fighter_b": f["fighter_b"]} for f in event["fight_card"]]
    odds_objects = get_odds_for_matchups(event_name, card_matchups)

    # Build lookup
    odds_map = {}
    for o in odds_objects:
        key1 = (o.fighter_a, o.fighter_b)
        key2 = (o.fighter_b, o.fighter_a)
        odds_map[key1] = o.dict()
        odds_map[key2] = o.dict()

    # STEP 6: Full fight analysis
    results = []

    for fight in event["fight_card"]:
        a = fight["fighter_a"]
        b = fight["fighter_b"]

        a_prof = fighters[a]
        b_prof = fighters[b]

        # Compute features
        a_feat = compute_stats_features(a_prof)
        b_feat = compute_stats_features(b_prof)

        odds = odds_map.get((a, b), {"odds_a": None, "odds_b": None})

        # Build bundle for analysis
        bundle = {
            "event_name": event_name,
            "fighter_a": a_prof,
            "fighter_b": b_prof,
            "a_features": a_feat,
            "b_features": b_feat,
            "odds": odds
        }

        analysis_out = run_full_analysis_nonstream(bundle)

        results.append({
            "fighter_a": a_prof,
            "fighter_b": b_prof,
            "odds": odds,
            "analysis": analysis_out.get("analysis"),
            "prediction": analysis_out.get("prediction"),
            "value_notes": analysis_out.get("value_notes")
        })

    # STEP 7: Parlays
    parlays = build_parlays(results)

    # STEP 8: Full payload
    output = {
        "event_name": event["event_name"],
        "event_date": event["event_date"],
        "location": event["location"],
        "generated_at": datetime.utcnow().isoformat(),
        "fights": results,
        "parlays": parlays
    }

    return output


# --------------------------------------------------------------
# RUN APP (for local debugging)
# --------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
