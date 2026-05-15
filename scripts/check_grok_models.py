import os
import httpx

key = os.getenv("GROQ_API_KEY")
resp = httpx.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"})
if resp.status_code == 200:
    models = resp.json()["data"]
    print("Modèles Groq disponibles :")
    for m in models:
        print(f"  - {m['id']}")
else:
    print(f"Erreur {resp.status_code}: {resp.text[:200]}")
