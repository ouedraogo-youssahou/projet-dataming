import os
import httpx

key = os.getenv("GROQ_API_KEY")
models = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768"
]

for model in models:
    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 20},
            timeout=15
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"].strip()
            print(f"✅ {model}: {content}")
        else:
            print(f"❌ {model}: {resp.status_code} - {resp.text[:100]}")
    except Exception as e:
        print(f"❌ {model}: {e}")
