import os

import requests
from dotenv import load_dotenv

load_dotenv()

resposta = requests.post(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json",
    },
    json={
        "model": "google/gemma-4-26b-a4b-it:free",
        "messages": [{"role": "user", "content": "diga oi"}],
    },
    timeout=30,
)
print("Status:", resposta.status_code)
print("Corpo:", resposta.text)
print("Headers relevantes:")
for h in resposta.headers:
    if "rate" in h.lower() or "limit" in h.lower():
        print(f"  {h}: {resposta.headers[h]}")