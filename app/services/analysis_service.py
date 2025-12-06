import logging
from typing import Dict, Any, List

from app.schemas import FightPair
from app.utils.gpt_safe import gpt_safe_call

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Compute simple statistical features
# (placeholder – you can extend later with real UFC data)
# ---------------------------------------------------------

def compute_stats_features(fight_card: List[FightPair]) -> Dict[str, Any]:
    """
    Produces basic structural metadata that later gets fed into GPT
    for the final analysis prompt.
    """

    return {
        "num_fights": len(fight_card),
        "fighters": [
            {"a": f.fighter_a, "b": f.fighter_b, "weight_class": f.weight_class}
            for f in fight_card
        ]
    }

# ---------------------------------------------------------
# Build the prompt GPT will use for predictions
# ---------------------------------------------------------

def build_analysis_prompt(event_json: Dict[str, Any], stats: Dict[str, Any]) -> str:
    """
    Creates the prompt sent to GPT to generate:
    - fight-by-fight predictions
    - reasoning
    - suggested parlay legs
    """

    event_name = event_json.get("event_name", "Unknown Event")
    fight_card = stats.get("fighters", [])

    prompt = (
        f"You are an MMA fight analyst.\n"
        f"Event: {event_name}\n"
        f"Number of fights: {stats['num_fights']}\n\n"
        f"For each fight, predict:\n"
        f" - Winner\n"
        f" - Method (KO/TKO, SUB, DEC)\n"
        f" - Confidence 1-10\n"
        f" - Key analytics (reach, style, pace, etc.)\n\n"
        f"Then generate:\n"
        f" - A safe parlay\n"
        f" - A longshot parlay\n\n"
        f"Fight card:\n"
    )

    for f in fight_card:
        wc = f["weight_class"] or "Unknown"
        prompt += f"- {f['a']} vs {f['b']} ({wc})\n"

    prompt += "\nReturn ONLY JSON in this format:\n"
    prompt += "{ 'predictions': [...], 'parlays': {...} }"

    return prompt

# ---------------------------------------------------------
# Run full GPT analysis workflow
# ---------------------------------------------------------

def run_full_analysis(event_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Bundle:
    1. Compute stats features
    2. Build GPT prompt
    3. Call GPT safely
    4. Parse JSON
    """

    stats = compute_stats_features(event_json["fight_card"])
    prompt = build_analysis_prompt(event_json, stats)

    raw = gpt_safe_call([prompt])

    try:
        data = eval(raw)  # expected JSON-like structure
    except Exception:
        logger.error("GPT returned malformed analysis JSON.")
        data = {}

    return data
