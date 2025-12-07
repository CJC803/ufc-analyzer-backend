import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gpt_safe_call(inputs: list[str]) -> str:
    """
    Wrapper around OpenAI Responses API using the new SDK format.
    Accepts a LIST OF STRINGS and joins them into a single input block.
    """

    try:
        # Combine all message strings into one payload
        final_input = "\n\n".join(inputs)

        response = client.responses.create(
            model="gpt-4o-mini",
            input=final_input,
            max_output_tokens=500,
            temperature=0.4,
        )

        # New SDK returns output at:
        # response.output[0].content[0].text
        output_text = response.output_text

        return output_text.strip()

    except Exception as e:
        logger.error(f"GPT call failed: {e}")
        return "{}"
