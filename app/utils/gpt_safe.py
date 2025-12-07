def gpt_safe_call(messages):
    try:
        # messages can now be raw strings OR dicts
        if isinstance(messages[0], str):
            messages = [{"role": "user", "content": messages[0]}]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.4
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"GPT call failed: {e}")
        return ""
