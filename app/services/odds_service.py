import json
from app.utils.openai_client import run

def generate_synthetic_odds(
    fighter_a: str,
    fighter_b: str,
    a_profile=None,
    b_profile=None
):
    prompt = f"""
    Generate realistic *synthetic* MMA betting odds for:

    Fighter A: {fighter_a}
    Fighter B: {fighter_b}

    Consider:
    - Win/loss trends
    - Finishing rate
    - Recent momentum
    - Size / reach
    - Experience
    - Age curve

    Output JSON ONLY:

    {{
      "fighter_a": "{fighter_a}",
      "fighter_b": "{fighter_b}",
      "american_odds": {{
         "a": "", 
         "b": ""
      }},
      "implied_probability": {{
         "a": 0.0,
         "b": 0.0
      }},
      "confidence": 0.0
    }}
    """

    raw = run([{"role": "user", "content": prompt}], model="gpt-4o-mini")

    try:
        return json.loads(raw)
    except:
        return {
            "fighter_a": fighter_a,
            "fighter_b": fighter_b,
            "american_odds": {"a": "-110", "b": "-110"},
            "implied_probability": {"a": 0.50, "b": 0.50},
            "confidence": 0.5,
        }
