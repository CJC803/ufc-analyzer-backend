import logging
from typing import List, Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()

def run(messages: List[Dict[str, str]]) -> str:
    """
    Minimal safe wrapper around OpenAI's chat completion API.
    This is a placeholder so the backend can boot without failing.
    Replace with your preferred model + streaming logic later.
    """
    logger.warning("Using placeholder OpenAI run() function.")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=1000,
    )

    return response.choices[0].message.get("content", "")


def run_stream(messages: List[Dict[str, str]]):
    """
    Placeholder streaming generator.
    Returns a fake generator so FastAPI dependencies don't explode.
    Replace with real streaming later.
    """
    logger.warning("Using placeholder OpenAI run_stream() function (no real streaming).")
    
    fake_text = "Streaming is not yet implemented."
    for chunk in fake_text.split():
        yield chunk
