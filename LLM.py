from groq import Groq

# Initialize Groq client once
# client = Groq(api_key="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")
# client = Groq(api_key="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")
client = Groq(api_key="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")

def LLM(system_prompt="You are a Smart Financial Advisor.", user_query="Hello!!"):
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
            stream=True
        )

        output = ""
        for chunk in completion:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                output += delta.content
        return output

    except Exception as e:
        return f"⚠️ Error generating response: {str(e)}"
