import os
import time
import threading
import requests

from flask import Flask


# ==================================================
# تنظیمات
# ==================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN تنظیم نشده است.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY تنظیم نشده است.")


TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.5-flash:generateContent"
)


# ==================================================
# متغیرهای ربات
# ==================================================

offset = 0

ai_users = set()

chat_history = {}


# ==================================================
# Flask برای Render
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

    app.run(
        host="0.0.0.0",
        port=port
    )


# ==================================================
# ارسال پیام
# ==================================================

def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    try:

        response = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            json=data,
            timeout=30
        )

        return response.json()

    except Exception as e:

        print("❌ خطا در ارسال پیام:", e)

        return None


# ==================================================
# حذف پیام
# ==================================================

def delete_message(chat_id, message_id):

    try:

        requests.post(
            f"{TELEGRAM_URL}/deleteMessage",
            data={
                "chat_id": chat_id,
                "message_id": message_id
            },
            timeout=30
        )

    except Exception as e:

        print("❌ خطا در حذف پیام:", e)


# ==================================================
# ارتباط با Gemini
# ==================================================

def ask_gemini(chat_id, user_text):

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append(
        {
            "role": "user",
            "parts": [
                {
                    "text": user_text
                }
            ]
        }
    )

    # فقط 10 پیام آخر برای جلوگیری از بزرگ شدن درخواست
    history = chat_history[chat_id][-10:]

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    data = {
        "contents": history
    }

    try:

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=data,
            timeout=60
        )

        print("Gemini Status:", response.status_code)

        result = response.json()

        if response.status_code == 200:

            answer = (
                result["candidates"][0]
                ["content"]["parts"][0]
                ["text"]
            )

            chat_history[chat_id].append(
                {
                    "role": "model",
                    "parts": [
                        {
                            "text": answer
                        }
                    ]
                }
            )

            return answer

        else:

            print("❌ Gemini Error:")
            print(result)

            return (
                "❌ متأسفانه فعلاً نتونستم "
                "از هوش مصنوعی جواب بگیرم.\n"
                "چند لحظه دیگه دوباره امتحان کن."
            )

    except Exception as e:

        print("❌ Gemini Exception:", e)

        return (
            "❌ هنگام ارتباط با هوش مصنوعی "
            "مشکلی پیش اومد."
        )


# ==================================================
# پردازش ربات تلگرام
# ==================================================

def telegram_bot():

    global offset

    print("🤖 ربات تلگرام روشن شد!")

    while True:

        try:

            response = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params={
                    "offset": offset,
                    "timeout": 30
                },
                timeout=40
            )

            data = response.json()

            if not data.get("ok"):

                print("❌ خطای Telegram:")
                print(data)

                time.sleep(3)
                continue

            for update in data["result"]:

                offset = update["update_id"] + 1


                # ==========================================
                # دکمه‌های Inline
                # ==========================================

                if "callback_query" in update:

                    callback = update["callback_query"]

                    callback_id = callback["id"]

                    chat_id = callback["message"]["chat"]["id"]

                    button = callback["data"]


                    # تأیید کلیک روی دکمه

                    try:

                        requests.post(
                            f"{TELEGRAM_URL}/answerCallbackQuery",
                            data={
                                "callback_query_id": callback_id
                            },
                            timeout=30
                        )

                    except Exception as e:

                        print(
                            "❌ Callback Error:",
                            e
                        )


                    # ==================================
                    # درباره ربات
                    # ==================================

                    if button == "about":

                        send_message(
                            chat_id,

                            "🤖 درباره ربات\n\n"
                            "این ربات یک دستیار هوشمند "
                            "تلگرامی است که با استفاده "
                            "از Gemini API ساخته شده است.\n\n"
                            "✨ در ساخت و توسعه این ربات "
                            "نیز از هوش مصنوعی ChatGPT "
                            "کمک گرفته شده است."
                        )


                    # ==================================
                    # هوش مصنوعی
                    # ==================================

                    elif button == "ai":

                        ai_users.add(chat_id)

                        if chat_id not in chat_history:

                            chat_history[chat_id] = []

                        send_message(
                            chat_id,

                            "🧠 حالت هوش مصنوعی فعال شد!\n\n"
                            "پیامت رو بفرست تا جواب بدم.\n\n"
                            "برای خروج از این حالت بنویس:\n"
                            "/stop"
                        )


                    continue


                # ==========================================
                # پیام معمولی
                # ==========================================

                if "message" not in update:
                    continue

                message = update["message"]

                chat_id = message["chat"]["id"]

                text = message.get("text", "").strip()

                print(
                    f"📩 پیام از {chat_id}: {text}"
                )


                # ==========================================
                # /start
                # ==========================================

                if text == "/start":

                    # اگر قبلاً در حالت AI بوده
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
                        "برای شروع، یکی از گزینه‌های "
                        "زیر رو انتخاب کن 👇",

                        keyboard
                    )

                    continue


                # ==========================================
                # /stop
                # ==========================================

                if text == "/stop":

                    ai_users.discard(chat_id)

                    chat_history.pop(
                        chat_id,
                        None
                    )

                    send_message(
                        chat_id,
                        "🛑 حالت هوش مصنوعی خاموش شد."
                    )

                    continue


                # ==========================================
                # حالت هوش مصنوعی
                # ==========================================

                if chat_id in ai_users:

                    # ارسال پیام فکر کردن
                    thinking_response = send_message(
                        chat_id,
                        "🧠 دارم فکر می‌کنم..."
                    )

                    # گرفتن پاسخ Gemini
                    answer = ask_gemini(
                        chat_id,
                        text
                    )

                    # ارسال پاسخ اصلی
                    send_message(
                        chat_id,
                        answer
                    )

                    # حذف پیام فکر کردن
                    if thinking_response:

                        try:

                            if thinking_response.get("ok"):

                                thinking_message_id = (
                                    thinking_response
                                    ["result"]
                                    ["message_id"]
                                )

                                delete_message(
                                    chat_id,
                                    thinking_message_id
                                )

                        except Exception as e:

                            print(
                                "❌ خطا در حذف پیام فکر کردن:",
                                e
                            )

                    continue


                # ==========================================
                # سلام
                # ==========================================

                if text in ["سلام", "سلام!", "سلام 👋"]:

                    send_message(
                        chat_id,
                        "سلام! 👋 خوش اومدی!"
                    )

                    continue


                # ==========================================
                # پیام ناشناخته
                # ==========================================

                send_message(
                    chat_id,

                    "🤔 متوجه نشدم.\n\n"
                    "برای دیدن منوی ربات "
                    "/start رو بفرست."
                )


        except Exception as e:

            print(
                "❌ خطای کلی ربات:",
                e
            )

            time.sleep(3)


# ==================================================
# شروع برنامه
# ==================================================

if __name__ == "__main__":

    # اجرای Flask در Thread جدا
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    # اجرای ربات تلگرام
    telegram_bot()
