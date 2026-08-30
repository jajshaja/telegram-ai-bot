import os
import json
import time
import requests


# ==========================================
# دریافت کلیدها از Environment Variables
# ==========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ==========================================
# بررسی وجود کلیدها
# ==========================================

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN تنظیم نشده است.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY تنظیم نشده است.")


# ==========================================
# تنظیمات
# ==========================================

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.5-flash:generateContent"
)

offset = 0

# کاربرانی که حالت هوش مصنوعی را فعال کرده‌اند
ai_users = set()

# تاریخچه مکالمه کاربران
chat_history = {}

print("🤖 ربات روشن شد!")


# ==========================================
# ارسال پیام به تلگرام
# ==========================================

def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps(keyboard)

    try:
        requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            data=data,
            timeout=30
        )

    except Exception as e:
        print("❌ خطا در ارسال پیام:", e)


# ==========================================
# ارتباط با Gemini
# ==========================================

def ask_gemini(chat_id, user_text):

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    # پیام کاربر
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

    # فقط ۱۰ پیام آخر
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

        result = response.json()

        print("Gemini Status:", response.status_code)

        # ==================================
        # پاسخ موفق
        # ==================================

        if response.status_code == 200:

            answer = (
                result["candidates"][0]
                ["content"]["parts"][0]
                ["text"]
            )

            # ذخیره پاسخ Gemini
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

        # ==================================
        # خطای Gemini
        # ==================================

        else:

            print("❌ Gemini Error:")
            print(result)

            return (
                "❌ متأسفانه فعلاً نتونستم از "
                "هوش مصنوعی جواب بگیرم.\n\n"
                "چند لحظه دیگه دوباره امتحان کن."
            )

    except Exception as e:

        print("❌ Gemini Exception:", e)

        return (
            "❌ هنگام ارتباط با هوش مصنوعی "
            "مشکلی پیش اومد."
        )


# ==========================================
# حلقه اصلی ربات
# ==========================================

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

        if data["ok"]:

            for update in data["result"]:

                # جلو بردن offset
                offset = update["update_id"] + 1


                # ==================================
                # دکمه‌های شیشه‌ای
                # ==================================

                if "callback_query" in update:

                    callback = update["callback_query"]

                    chat_id = callback["message"]["chat"]["id"]

                    callback_id = callback["id"]

                    button = callback["data"]


                    # حذف Loading دکمه
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

                            "این ربات با هدف ارائه "
                            "یک دستیار هوشمند و کاربردی "
                            "در محیط تلگرام ساخته شده است.\n\n"

                            "🧠 فناوری هوش مصنوعی این "
                            "ربات توسط Gemini API "
                            "تأمین می‌شود.\n\n"

                            "✨ در ساخت و توسعه این "
                            "ربات نیز از هوش مصنوعی "
                            "ChatGPT کمک گرفته شده است."
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

                            "🧠 حالت هوش مصنوعی "
                            "فعال شد!\n\n"

                            "هر چیزی می‌خوای بپرس.\n\n"

                            "برای خروج از حالت AI "
                            "بنویس:\n"
                            "/stop"
                        )

                    continue


                # ==================================
                # پیام‌های معمولی
                # ==================================

                if "message" in update:

                    message = update["message"]

                    chat_id = message["chat"]["id"]

                    text = message.get(
                        "text",
                        ""
                    ).strip()

                    print(
                        "📩 پیام دریافت شد:",
                        text
                    )


                    # ==================================
                    # خروج از حالت AI
                    # ==================================

                    if text == "/stop":

                        ai_users.discard(chat_id)

                        chat_history.pop(
                            chat_id,
                            None
                        )

                        send_message(
                            chat_id,
                            "🛑 حالت هوش مصنوعی "
                            "خاموش شد."
                        )

                        continue


                    # ==================================
                    # حالت AI
                    # ==================================

                    if chat_id in ai_users:

                        print(
                            "🧠 ارسال پیام به Gemini..."
                        )

                        send_message(
                            chat_id,
                            "🧠 دارم فکر می‌کنم..."
                        )

                        answer = ask_gemini(
                            chat_id,
                            text
                        )

                        send_message(
                            chat_id,
                            answer
                        )

                        continue


                    # ==================================
                    # دستور /start
                    # ==================================

                    if text == "/start":

                        keyboard = {

                            "inline_keyboard": [

                                [
                                    {
                                        "text":
                                        "🤖 درباره ربات",

                                        "callback_data":
                                        "about"
                                    }
                                ],

                                [
                                    {
                                        "text":
                                        "🧠 هوش مصنوعی",

                                        "callback_data":
                                        "ai"
                                    }
                                ]

                            ]

                        }

                        send_message(

                            chat_id,

                            "🤖 به دستیار هوشمند "
                            "ما خوش آمدید!\n\n"

                            "این ربات با بهره‌گیری "
                            "از Gemini API طراحی شده "
                            "تا تجربه‌ای سریع، هوشمند "
                            "و کاربردی را در اختیار شما "
                            "قرار دهد.\n\n"

                            "👇 گزینه موردنظر خود "
                            "را انتخاب کنید:",

                            keyboard
                        )


                    # ==================================
                    # سلام
                    # ==================================

                    elif text == "سلام":

                        send_message(
                            chat_id,
                            "سلام! 👋 خوش اومدی!"
                        )


                    # ==================================
                    # پیام ناشناخته
                    # ==================================

                    else:

                        send_message(

                            chat_id,

                            "🤔 متوجه نشدم!\n"

                            "برای دیدن منوی ربات "
                            "/start رو بفرست."
                        )


    except Exception as e:

        print(
            "❌ خطای کلی:",
            e
        )

        time.sleep(3)
