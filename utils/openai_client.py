from typing import List, Dict, Any, Generator
from openai import OpenAI
from app.config import settings

# Create a global OpenAI client

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def run(
messages: List[Dict[str, Any]],
model: str = "gpt-4o-mini",
temperature: float = 0.2
) -> str:
"""
Standard non-streaming GPT call.
Used for all backend tasks except final analysis.
"""
response = client.chat.completions.create(
model=model,
messages=messages,
temperature=temperature
)
return response.choices[0].message.content

def run_stream(
messages: List[Dict[str, Any]],
model: str = "gpt-4o-mini",
temperature: float = 0.2
) -> Generator[str, None, None]:
"""
Streaming GPT call.
Yields tokens as they arrive.
Used ONLY for /analysis endpoint.
"""
stream = client.chat.completions.create(
model=model,
messages=messages,
temperature=temperature,
stream=True
)

```
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta and delta.content:
        yield delta.content
```
