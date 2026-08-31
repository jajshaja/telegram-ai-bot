import os
import time
import threading
import base64
import mimetypes
import requests
from flask import Flask

# ==================================================
# تنظیمات
# ==================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN تنظیم نشده است.")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY تنظیم نشده است.")

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
)

# ==================================================
# Flask
# ==================================================

app = Flask(__name__)


@app.route("/")
def home():
    return "🤖 Telegram AI Bot is running!"


@app.route("/health")
def health():
    return "OK"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ==================================================
# حافظه
# ==================================================

ai_users = set()
chat_history = {}
offset = 0


# ==================================================
# Telegram
# ==================================================

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    try:
        r = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            json=data,
            timeout=30
        )

        if not r.ok:
            print("❌ Telegram:", r.text)

        return r.json()

    except Exception as e:
        print("❌ send_message:", e)


def get_file(file_id):
    try:
        r = requests.get(
            f"{TELEGRAM_URL}/getFile",
            params={"file_id": file_id},
            timeout=30
        )

        data = r.json()

        if data.get("ok"):
            return data["result"].get("file_path")

        print("❌ getFile:", data)

    except Exception as e:
        print("❌ get_file:", e)


def download_file(file_path):
    try:
        url = (
            f"https://api.telegram.org/"
            f"file/bot{TELEGRAM_TOKEN}/{file_path}"
        )

        r = requests.get(url, timeout=60)

        if r.ok:
            return r.content

        print("❌ دانلود عکس:", r.status_code)

    except Exception as e:
        print("❌ download_file:", e)


# ==================================================
# Gemini
# ==================================================

def gemini_request(contents):
    try:
        r = requests.post(
            GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            },
            json={"contents": contents},
            timeout=120
        )

        print(f"📡 Gemini Status: {r.status_code}")

        if r.status_code != 200:
            print("❌ Gemini:", r.text)

            if r.status_code == 429:
                return "⏳ درخواست‌های Gemini بیش از حد مجاز شده.\nلطفاً کمی بعد دوباره امتحان کن."

            if r.status_code == 403:
                return "❌ دسترسی به Gemini رد شد. API Key را بررسی کن."

            if r.status_code == 400:
                return "❌ درخواست Gemini نامعتبر است."

            return "❌ Gemini فعلاً پاسخ نداد."

        data = r.json()
        parts = data.get("candidates", [{}])[0].get(
            "content", {}
        ).get("parts", [])

        answer = "".join(
            p.get("text", "")
            for p in parts
        )

        return answer or "❌ Gemini پاسخ خالی ارسال کرد."

    except requests.exceptions.Timeout:
        return "⏳ پاسخ Gemini خیلی طول کشید. دوباره امتحان کن."

    except Exception as e:
        print("❌ Gemini Error:", e)
        return "❌ ارتباط با Gemini برقرار نشد."


def ask_gemini(chat_id, text):
    history = chat_history.setdefault(chat_id, [])

    history.append({
        "role": "user",
        "parts": [{"text": text}]
    })

    answer = gemini_request(history[-10:])

    if answer:
        history.append({
            "role": "model",
            "parts": [{"text": answer}]
        })

    chat_history[chat_id] = history[-20:]

    return answer


def ask_gemini_image(chat_id, image, mime_type, caption):
    if not caption:
        caption = (
            "این تصویر را با دقت بررسی کن و "
            "توضیح مفیدی درباره آن بده."
        )

    encoded = base64.b64encode(image).decode("utf-8")

    history = chat_history.setdefault(chat_id, [])[-8:]

    contents = history + [{
        "role": "user",
        "parts": [
            {"text": caption},
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": encoded
                }
            }
        ]
    }]

    answer = gemini_request(contents)

    history.append({
        "role": "user",
        "parts": [{
            "text": f"[تصویر ارسال شد] {caption}"
        }]
    })

    history.append({
        "role": "model",
        "parts": [{"text": answer}]
    })

    chat_history[chat_id] = history[-20:]

    return answer


# ==================================================
# Callback دکمه‌ها
# ==================================================

def handle_callback(update):
    callback = update["callback_query"]
    chat_id = callback.get("message", {}).get(
        "chat", {}
    ).get("id")

    button = callback.get("data")

    try:
        requests.post(
            f"{TELEGRAM_URL}/answerCallbackQuery",
            data={"callback_query_id": callback["id"]},
            timeout=10
        )
    except:
        pass

    if button == "about":
        send_message(
            chat_id,
            "🤖 این ربات یک دستیار هوشمند تلگرامی است.\n\n"
            "🧠 پاسخ‌گویی با Gemini\n"
            "🖼️ تحلیل تصویر\n"
            "💬 حافظه مکالمه"
        )

    elif button == "ai":
        ai_users.add(chat_id)
        chat_history.setdefault(chat_id, [])

        send_message(
            chat_id,
            "🧠 حالت هوش مصنوعی فعال شد!\n\n"
            "پیامت رو بفرست.\n"
            "🖼️ عکس هم می‌تونی بفرستی.\n\n"
            "برای خروج:\n/stop"
        )


# ==================================================
# پردازش پیام
# ==================================================

def handle_message(message):
    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return

    text = message.get("text", "").strip()

    # --------------------------
    # /start
    # --------------------------

    if text == "/start":
        ai_users.discard(chat_id)

        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "🤖 درباره ربات",
                        "callback_data": "about"
                    }
                ],
                [
                    {
                        "text": "🧠 هوش مصنوعی",
                        "callback_data": "ai"
                    }
                ]
            ]
        }

        send_message(
            chat_id,
            "🤖 به ربات من خوش اومدی!\n\n"
            "برای شروع یکی از گزینه‌های زیر رو انتخاب کن 👇",
            keyboard
        )
        return

    # --------------------------
    # /stop
    # --------------------------

    if text == "/stop":
        ai_users.discard(chat_id)
        chat_history.pop(chat_id, None)

        send_message(
            chat_id,
            "🛑 حالت هوش مصنوعی خاموش شد."
        )
        return

    # --------------------------
    # عکس
    # --------------------------

    if "photo" in message:
        if chat_id not in ai_users:
            send_message(
                chat_id,
                "🖼️ اول حالت «🧠 هوش مصنوعی» رو فعال کن."
            )
            return

        photos = message.get("photo", [])

        if not photos:
            send_message(chat_id, "❌ اطلاعات عکس پیدا نشد.")
            return

        file_id = photos[-1].get("file_id")

        file_path = get_file(file_id)

        if not file_path:
            send_message(
                chat_id,
                "❌ نتونستم فایل عکس رو دریافت کنم."
            )
            return

        image = download_file(file_path)

        if not image:
            send_message(
                chat_id,
                "❌ دانلود عکس ناموفق بود."
            )
            return

        mime_type = (
            mimetypes.guess_type(file_path)[0]
            or "image/jpeg"
        )

        caption = message.get("caption", "").strip()

        print(
            f"🖼️ عکس دریافت شد | "
            f"Size: {len(image)} | "
            f"MIME: {mime_type}"
        )

        answer = ask_gemini_image(
            chat_id,
            image,
            mime_type,
            caption
        )

        send_message(chat_id, answer)
        return

    # --------------------------
    # متن معمولی
    # --------------------------

    if text and chat_id in ai_users:
        print(f"💬 User: {text}")

        answer = ask_gemini(
            chat_id,
            text
        )

        send_message(
            chat_id,
            answer
        )


# ==================================================
# دریافت پیام‌های Telegram
# ==================================================

def telegram_loop():
    global offset

    print("🤖 Telegram Bot Started")

    while True:
        try:
            r = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params={
                    "offset": offset,
                    "timeout": 30
                },
                timeout=40
            )

            data = r.json()

            if not data.get("ok"):
                print("❌ getUpdates:", data)
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1

                if "callback_query" in update:
                    handle_callback(update)

                elif "message" in update:
                    handle_message(
                        update["message"]
                    )

        except Exception as e:
            print("❌ Telegram Loop:", e)
            time.sleep(5)


# ==================================================
# شروع برنامه
# ==================================================

if __name__ == "__main__":

    threading.Thread(
        target=telegram_loop,
        daemon=True
    ).start()

    run_web_server()
