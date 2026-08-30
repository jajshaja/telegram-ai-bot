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
    raise ValueError("❌ TELEGRAM_TOKEN تنظیم نشده است.")

if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY تنظیم نشده است.")


TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# مدل Gemini
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    "v1beta/models/gemini-3.5-flash:generateContent"
)


# ==================================================
# Flask / Render
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

    print(f"🌐 Flask روی پورت {port} اجرا شد.")

    app.run(
        host="0.0.0.0",
        port=port
    )


# ==================================================
# متغیرهای ربات
# ==================================================

offset = 0

# کاربرانی که حالت هوش مصنوعی برایشان فعال است
ai_users = set()

# تاریخچه مکالمه هر کاربر
chat_history = {}


# ==================================================
# ارسال پیام تلگرام
# ==================================================

def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard is not None:
        data["reply_markup"] = keyboard

    try:

        response = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            json=data,
            timeout=30
        )

        result = response.json()

        print(
            f"📤 Telegram sendMessage Status: "
            f"{response.status_code}"
        )

        if not result.get("ok"):
            print("❌ Telegram sendMessage Error:")
            print(result)

        return result

    except Exception as e:

        print("❌ خطا در send_message:")
        print(e)

        return None


# ==================================================
# حذف پیام
# ==================================================

def delete_message(chat_id, message_id):

    try:

        response = requests.post(
            f"{TELEGRAM_URL}/deleteMessage",
            data={
                "chat_id": chat_id,
                "message_id": message_id
            },
            timeout=30
        )

        result = response.json()

        print(
            f"🗑 deleteMessage Status: "
            f"{response.status_code}"
        )

        if not result.get("ok"):
            print("⚠️ حذف پیام ناموفق بود:")
            print(result)

        return result

    except Exception as e:

        print("❌ خطا در حذف پیام:")
        print(e)

        return None


# ==================================================
# ارتباط با Gemini
# ==================================================

def ask_gemini(chat_id, user_text):

    print("========================================")
    print("🧠 شروع درخواست Gemini")
    print(f"👤 Chat ID: {chat_id}")
    print(f"💬 متن کاربر: {user_text}")
    print("========================================")

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

    # فقط 10 پیام آخر
    history = chat_history[chat_id][-10:]

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    data = {
        "contents": history
    }

    try:

        print("📡 در حال ارسال درخواست به Gemini...")

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=data,
            timeout=60
        )

        print(
            f"📡 Gemini Status: "
            f"{response.status_code}"
        )

        print(
            f"📦 Gemini Response Length: "
            f"{len(response.text)}"
        )

        # ------------------------------------------
        # موفق
        # ------------------------------------------

        if response.status_code == 200:

            try:

                result = response.json()

                print("✅ پاسخ Gemini دریافت شد.")

                candidates = result.get(
                    "candidates",
                    []
                )

                if not candidates:

                    print(
                        "❌ Gemini هیچ candidate ای برنگرداند."
                    )

                    print(result)

                    return (
                        "❌ هوش مصنوعی پاسخی برنگرداند."
                    )

                content = candidates[0].get(
                    "content",
                    {}
                )

                parts = content.get(
                    "parts",
                    []
                )

                if not parts:

                    print(
                        "❌ Gemini قسمت text ندارد."
                    )

                    print(result)

                    return (
                        "❌ پاسخ هوش مصنوعی "
                        "قابل دریافت نبود."
                    )

                answer = parts[0].get(
                    "text",
                    ""
                )

                if not answer:

                    return (
                        "❌ هوش مصنوعی پاسخ خالی ارسال کرد."
                    )

                # ذخیره پاسخ در تاریخچه
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

                print("✅ پاسخ Gemini با موفقیت دریافت شد.")
                print("========================================")

                return answer

            except Exception as e:

                print(
                    "❌ خطا در پردازش JSON Gemini:"
                )

                print(e)

                print("Raw response:")
                print(response.text)

                return (
                    "❌ پاسخ هوش مصنوعی "
                    "قابل پردازش نبود."
                )

        # ------------------------------------------
        # خطای Gemini
        # ------------------------------------------

        else:

            print("❌ Gemini Error:")
            print(response.text)

            # خطای API Key
            if response.status_code == 400:

                return (
                    "❌ درخواست ارسال‌شده به Gemini "
                    "اشکال دارد."
                )

            # دسترسی
            elif response.status_code == 403:

                return (
                    "❌ دسترسی به Gemini رد شد.\n\n"
                    "احتمالاً API Key یا دسترسی API "
                    "مشکل دارد."
                )

            # محدودیت
            elif response.status_code == 429:

                return (
                    "⏳ درخواست‌های Gemini بیش از حد مجاز شده.\n"
                    "لطفاً کمی بعد دوباره امتحان کن."
                )

            # سرور Gemini
            elif response.status_code == 503:

                return (
                    "⏳ سرویس Gemini فعلاً شلوغ است.\n"
                    "لطفاً چند لحظه بعد دوباره امتحان کن."
                )

            else:

                return (
                    "❌ متأسفانه فعلاً نتونستم "
                    "از هوش مصنوعی جواب بگیرم.\n"
                    "چند لحظه دیگه دوباره امتحان کن."
                )

    except requests.exceptions.Timeout:

        print("❌ درخواست Gemini Timeout شد.")

        return (
            "⏳ پاسخ Gemini خیلی طول کشید.\n"
            "لطفاً دوباره امتحان کن."
        )

    except requests.exceptions.RequestException as e:

        print(
            "❌ خطای ارتباط با Gemini:"
        )

        print(e)

        return (
            "❌ ارتباط با هوش مصنوعی برقرار نشد."
        )

    except Exception as e:

        print(
            "❌ خطای ناشناخته در Gemini:"
        )

        print(e)

        return (
            "❌ هنگام ارتباط با هوش مصنوعی "
            "مشکلی پیش آمد."
        )


# ==================================================
# پردازش Callback دکمه‌ها
# ==================================================

def handle_callback(update):

    callback = update["callback_query"]

    callback_id = callback["id"]

    message = callback.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    button = callback.get(
        "data",
        ""
    )

    print(
        f"🔘 Callback دریافت شد: {button}"
    )

    # تأیید کلیک
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
            "❌ Callback Answer Error:",
            e
        )


    # ----------------------------------------------
    # درباره ربات
    # ----------------------------------------------

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


    # ----------------------------------------------
    # هوش مصنوعی
    # ----------------------------------------------

    elif button == "ai":

        ai_users.add(chat_id)

        if chat_id not in chat_history:
            chat_history[chat_id] = []

        send_message(
            chat_id,

            "🧠 حالت هوش مصنوعی فعال شد!\n\n"
            "پیامت رو بفرست تا جواب بدم.\n\n"
            "برای خروج از این حالت:\n"
            "/stop"
        )


# ==================================================
# پردازش پیام
# ==================================================

def handle_message(message):

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    text = message.get(
        "text",
        ""
    ).strip()

    if not chat_id:
        return

    print("========================================")
    print(f"📩 پیام دریافت شد")
    print(f"👤 Chat ID: {chat_id}")
    print(f"💬 Text: {text}")
    print("========================================")


    # ==========================================
    # /start
    # ==========================================

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
            "برای شروع، یکی از گزینه‌های "
            "زیر رو انتخاب کن 👇",

            keyboard
        )

        return


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

        return


    # ==========================================
    # حالت هوش مصنوعی
    # ==========================================

    if chat_id in ai_users:

        print("🧠 کاربر در حالت هوش مصنوعی است.")

        # پیام موقت
        thinking_response = send_message(
            chat_id,
            "🧠 دارم فکر می‌کنم..."
        )

        thinking_message_id = None

        if thinking_response:

            if thinking_response.get("ok"):

                thinking_message_id = (
                    thinking_response
                    .get("result", {})
                    .get("message_id")
                )

                print(
                    f"🧠 Thinking Message ID: "
                    f"{thinking_message_id}"
                )

        print("🧠 ارسال پیام به Gemini...")

        answer = ask_gemini(
            chat_id,
            text
        )

        print("📤 ارسال پاسخ Gemini به کاربر...")

        send_message(
            chat_id,
            answer
        )

        # حذف پیام «دارم فکر می‌کنم»
        if thinking_message_id:

            print(
                "🗑 در حال حذف پیام «دارم فکر می‌کنم»..."
            )

            delete_message(
                chat_id,
                thinking_message_id
            )

        print("✅ پردازش پیام تمام شد.")

        return


    # ==========================================
    # سلام
    # ==========================================

    if text in [
        "سلام",
        "سلام!",
        "سلام 👋"
    ]:

        send_message(
            chat_id,
            "سلام! 👋 خوش اومدی!"
        )

        return


    # ==========================================
    # پیام ناشناخته
    # ==========================================

    send_message(
        chat_id,

        "🤔 متوجه نشدم.\n\n"
        "برای دیدن منوی ربات "
        "/start رو بفرست."
    )


# ==================================================
# دریافت پیام‌های تلگرام
# ==================================================

def telegram_bot():

    global offset

    print("🤖 ربات تلگرام روشن شد!")

    # تست اتصال به Telegram
    try:

        me_response = requests.get(
            f"{TELEGRAM_URL}/getMe",
            timeout=30
        )

        me_result = me_response.json()

        if me_result.get("ok"):

            bot_username = (
                me_result["result"]
                .get("username")
            )

            print(
                f"✅ اتصال به Telegram موفق بود: "
                f"@{bot_username}"
            )

        else:

            print(
                "❌ اتصال به Telegram ناموفق:"
            )

            print(me_result)

    except Exception as e:

        print(
            "❌ خطا در تست Telegram:",
            e
        )


    # ==========================================
    # حلقه اصلی
    # ==========================================

    while True:

        try:

            print("🔄 در حال دریافت پیام‌های Telegram...")

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

                print(
                    "❌ Telegram getUpdates Error:"
                )

                print(data)

                time.sleep(3)

                continue


            updates = data.get(
                "result",
                []
            )

            if updates:

                print(
                    f"📥 تعداد آپدیت‌های جدید: "
                    f"{len(updates)}"
                )


            for update in updates:

                offset = update["update_id"] + 1

                # ----------------------------------
                # Callback
                # ----------------------------------

                if "callback_query" in update:

                    handle_callback(update)

                    continue


                # ----------------------------------
                # Message
                # ----------------------------------

                if "message" in update:

                    handle_message(
                        update["message"]
                    )


        except requests.exceptions.Timeout:

            # Timeout در getUpdates طبیعی است
            continue

        except Exception as e:

            print(
                "❌ خطای کلی Telegram Bot:"
            )

            print(e)

            time.sleep(3)


# ==================================================
# شروع برنامه
# ==================================================

if __name__ == "__main__":

    print("========================================")
    print("🚀 Starting Telegram AI Bot")
    print("========================================")

    # Flask برای Render
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    # ربات تلگرام
    telegram_bot()
