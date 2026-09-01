import os
import requests

API_KEY = os.getenv("CEREBRAS_API_KEY")

if not API_KEY:
    print("❌ CEREBRAS_API_KEY پیدا نشد!")
    exit()

url = "https://api.cerebras.ai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "gpt-oss-120b",
    "messages": [
        {
            "role": "user",
            "content": "سلام! فقط بنویس: اتصال Cerebras موفق بود."
        }
    ],
    "temperature": 0.7,
    "max_tokens": 100
}

try:
    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=30
    )

    print("📡 Cerebras Status:", response.status_code)
    print("📨 Response:")
    print(response.text)

except Exception as e:
    print("❌ خطا:")
    print(e)
