import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def gpt_safe_call(messages: list) -> str:
    """
    Safe wrapper around OpenAI chat completions.
    Accepts FULL message objects:
      [{"role": "user", "content": "..."}]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,   # <-- NO MORE REWRAPPING
            temperature=0.4
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"GPT call failed: {e}")
        return "{}"
