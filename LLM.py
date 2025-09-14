# LLM.py
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not set. Add it to environment or .env")

client = Groq(api_key=GROQ_API_KEY)


def run_llm(system_prompt="You are a Smart Financial Advisor.", user_query="Hello!!"):
    """
    Streams tokens from Groq LLM as they arrive.
    Yields: string chunks
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
            temperature=0.6,
            max_completion_tokens=1024,
            top_p=1,
            stream=True,
        )

        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        yield f"⚠️ Error generating response: {str(e)}"
