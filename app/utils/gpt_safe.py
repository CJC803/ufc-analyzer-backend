import logging
import os
from typing import Any, List
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gpt_safe_call(messages: List[Any]) -> str:
    """
    Accepts either:
      - ["user prompt"]
      - [{"role": "user", "content": "..."}]
    
    Always converts to the correct ChatCompletion format.
    """

    # Normalize messages into OpenAI format
    formatted = []

    for m in messages:
        if isinstance(m, str):
            formatted.append({"role": "user", "content": m})
        elif isinstance(m, dict):
            # already a formatted message
            formatted.append(m)
        else:
            logger.error(f"Invalid message type: {type(m)} — {m}")
            continue

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=formatted,
            temperature=0.4
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"GPT call failed: {e}")
        return "{}"
