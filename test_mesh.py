import urllib.request
import urllib.error
import json

API_KEY = "rsk_01M1CCKEY1TWCS2RJXXRX33712"

URL = "https://api.meshapi.ai/v1/chat/completions"

data = {
    "model": "auto",
    "messages": [
        {
            "role": "user",
            "content": "سلام! فقط بگو اتصال MeshAPI موفق بود."
        }
    ]
}

payload = json.dumps(data).encode("utf-8")

request = urllib.request.Request(
    URL,
    data=payload,
    method="POST"
)

request.add_header("Content-Type", "application/json")
request.add_header("Authorization", "Bearer " + API_KEY)

print("===================================")
print("🤖 MeshAPI Test")
print("===================================")
print("📡 در حال ارسال درخواست...")
print()

try:
    response = urllib.request.urlopen(request, timeout=60)

    status = response.status
    body = response.read().decode("utf-8")

    print("HTTP Status:", status)
    print()
    print("✅ اتصال به MeshAPI موفق بود!")
    print()
    print("📨 پاسخ:")
    print(body)

except urllib.error.HTTPError as e:
    print("❌ HTTP Error:", e.code)
    print()
    print(e.read().decode("utf-8"))

except urllib.error.URLError as e:
    print("❌ خطای اتصال:")
    print(e)

except Exception as e:
    print("❌ خطای غیرمنتظره:")
    print(e)
