import os
import logging
import requests
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")

BASE_URL = (
    "https://api.the-odds-api.com/v4/sports/mma_mixed_martial_arts/odds"
)


def get_odds_for_matchups(matchups: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Given a list of fighter matchups:
    [
        { "fighter_a": "Jon Jones", "fighter_b": "Stipe Miocic" },
        ...
    ]

    Returns:
        {
            "Jon Jones vs Stipe Miocic": {
                "fighter_a_odds": -210,
                "fighter_b_odds": +180,
                "source": "the-odds-api"
            }
        }
    """

    # No API key? return placeholder odds so app DOES NOT BREAK
    if not THE_ODDS_API_KEY:
        logger.warning("THE_ODDS_API_KEY missing — using placeholder odds.")
        return {
            f"{m['fighter_a']} vs {m['fighter_b']}": {
                "fighter_a_odds": -110,
                "fighter_b_odds": -110,
                "source": "placeholder"
            }
            for m in matchups
        }

    logger.info("Fetching MMA odds from TheOddsAPI...")

    try:
        response = requests.get(
            BASE_URL,
            params={
                "apiKey": THE_ODDS_API_KEY,
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "american"
            },
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"TheOddsAPI returned {response.status_code}: {response.text}")
            return {}

        data = response.json()
        output = {}

        # Preprocess user matchups for fuzzy matching
        normalized_matchups = [
            {
                "a": m["fighter_a"].lower(),
                "b": m["fighter_b"].lower(),
                "raw": m
            }
            for m in matchups
        ]

        for event in data:
            if not event.get("bookmakers"):
                continue

            # Pick first bookmaker for simplicity
            book = event["bookmakers"][0]
            market = book.get("markets", [])[0]
            outcomes = market.get("outcomes", [])

            if len(outcomes) != 2:
                continue

            name1 = outcomes[0]["name"].lower()
            name2 = outcomes[1]["name"].lower()

            # Attempt to match against each user matchup
            for nm in normalized_matchups:
                if (name1 in nm["a"] or name1 in nm["b"]) or (name2 in nm["a"] or name2 in nm["b"]):

                    key = f"{nm['raw']['fighter_a']} vs {nm['raw']['fighter_b']}"

                    output[key] = {
                        "fighter_a_odds": outcomes[0]["price"],
                        "fighter_b_odds": outcomes[1]["price"],
                        "source": "the-odds-api"
                    }

        return output

    except Exception as e:
        logger.error(f"Odds fetch failed: {e}")
        return {}
