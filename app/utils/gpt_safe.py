import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gpt_safe_call(messages: list[str]) -> str:
    """
    Wrapper around OpenAI ChatCompletion that:
      - prevents crashes from API errors
      - logs errors for debugging
      - returns a safe fallback string if API fails
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": msg} for msg in messages],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"GPT call failed: {e}")
        return "{}"
