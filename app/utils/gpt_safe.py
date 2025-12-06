import time
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(**name**)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def gpt_safe_call(
messages: List[Dict[str, Any]],
model: str = "gpt-4o-mini",
temperature: float = 0.2,
max_retries: int = 5,           # Moderate retry strategy
initial_wait: float = 1.0,      # 1 second
backoff_factor: float = 2.0,    # Exponential backoff
) -> str:
"""
Safe GPT wrapper with retry and exponential backoff.
Returns the assistant message text.
"""

```
attempt = 0
wait_time = initial_wait

while attempt < max_retries:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature
        )

        return response.choices[0].message.content

    except Exception as e:
        attempt += 1
        logger.warning(f"GPT call failed (attempt {attempt}/{max_retries}): {e}")

        if attempt >= max_retries:
            logger.error("GPT call failed after max retries.")
            raise RuntimeError("GPT call failed after multiple retries.")

        time.sleep(wait_time)
        wait_time *= backoff_factor  # exponential increase
```

def gpt_structured_call(
messages: List[Dict[str, Any]],
response_format: Dict[str, Any],
model: str = "gpt-4o-mini",
temperature: float = 0.2,
) -> Any:
"""
Wrapper when requesting 'response_format' structured output (JSON mode).
"""

```
try:
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format=response_format,
        temperature=temperature
    )
    return response.choices[0].message.parsed

except Exception as e:
    logger.error("GPT structured call failed:", e)
    raise
```
