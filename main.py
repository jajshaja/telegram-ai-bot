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

# مدل پایدار چندرسانه‌ای Gemini
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/{GEMINI_MODEL}:generateContent"
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
# دریافت اطلاعات فایل از Telegram
# ==================================================

def get_telegram_file(file_id):

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getFile",
            params={
                "file_id": file_id
            },
            timeout=30
        )

        result = response.json()

        if not result.get("ok"):

            print("❌ Telegram getFile Error:")
            print(result)

            return None

        return result["result"].get("file_path")

    except Exception as e:

        print("❌ خطا در get_telegram_file:")
        print(e)

        return None


# ==================================================
# دانلود فایل از Telegram
# ==================================================

def download_telegram_file(file_path):

    try:

        url = (
            f"https://api.telegram.org/"
            f"file/bot{TELEGRAM_TOKEN}/"
            f"{file_path}"
        )

        response = requests.get(
            url,
            timeout=60
        )

        if response.status_code != 200:

            print(
                "❌ خطا در دانلود فایل Telegram:",
                response.status_code
            )

            return None

        print(
            f"📥 فایل دانلود شد: "
            f"{len(response.content)} bytes"
        )

        return response.content

    except Exception as e:

        print("❌ خطا در دانلود فایل:")
        print(e)

        return None


# ==================================================
# تشخیص MIME تصویر
# ==================================================

def get_image_mime_type(file_path):

    mime_type, _ = mimetypes.guess_type(
        file_path
    )

    if mime_type and mime_type.startswith("image/"):
        return mime_type

    # Telegram معمولاً عکس را به شکل JPEG می‌دهد
    return "image/jpeg"


# ==================================================
# ارتباط متنی با Gemini
# ==================================================

def ask_gemini(chat_id, user_text):

    print("========================================")
    print("🧠 شروع درخواست Gemini")
    print(f"👤 Chat ID: {chat_id}")
    print(f"💬 متن کاربر: {user_text}")
    print("========================================")

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    # ذخیره پیام کاربر
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
            timeout=90
        )

        print(
            f"📡 Gemini Status: "
            f"{response.status_code}"
        )

        if response.status_code == 200:

            result = response.json()

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

            answer = ""

            for part in parts:

                if "text" in part:

                    answer += part["text"]

            if not answer:

                return (
                    "❌ هوش مصنوعی پاسخ خالی ارسال کرد."
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

            print(
                "✅ پاسخ Gemini با موفقیت دریافت شد."
            )

            return answer

        # ------------------------------
        # خطاهای Gemini
        # ------------------------------

        print("❌ Gemini Error:")
        print(response.text)

        if response.status_code == 400:

            return (
                "❌ درخواست ارسال‌شده به Gemini "
                "اشکال دارد."
            )

        elif response.status_code == 403:

            return (
                "❌ دسترسی به Gemini رد شد.\n\n"
                "احتمالاً API Key یا دسترسی API "
                "مشکل دارد."
            )

        elif response.status_code == 429:

            return (
                "⏳ درخواست‌های Gemini بیش از حد مجاز شده.\n"
                "لطفاً کمی بعد دوباره امتحان کن."
            )

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

        print("❌ خطای ارتباط با Gemini:")
        print(e)

        return (
            "❌ ارتباط با هوش مصنوعی برقرار نشد."
        )

    except Exception as e:

        print("❌ خطای ناشناخته در Gemini:")
        print(e)

        return (
            "❌ هنگام ارتباط با هوش مصنوعی "
            "مشکلی پیش آمد."
        )


# ==================================================
# تحلیل تصویر با Gemini
# ==================================================

def ask_gemini_image(
    chat_id,
    image_bytes,
    mime_type,
    user_text
):

    print("========================================")
    print("🖼️ شروع تحلیل تصویر توسط Gemini")
    print(f"👤 Chat ID: {chat_id}")
    print(f"📝 متن همراه تصویر: {user_text}")
    print(f"📦 MIME Type: {mime_type}")
    print(f"📏 Image Size: {len(image_bytes)} bytes")
    print("========================================")

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    if not user_text:

        user_text = (
            "این تصویر را با دقت بررسی کن و "
            "توضیح مفیدی درباره آن بده."
        )

    # تبدیل تصویر به Base64
    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    # ------------------------------------------------
    # تاریخچه متنی قبلی
    # ------------------------------------------------

    history = chat_history[chat_id][-8:]

    # ------------------------------------------------
    # پیام فعلی شامل متن + تصویر
    # ------------------------------------------------

    current_message = {
        "role": "user",
        "parts": [
            {
                "text": user_text
            },
            {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_base64
                }
            }
        ]
    }

    contents = history + [
        current_message
    ]

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    data = {
        "contents": contents
    }

    try:

        print("📡 در حال ارسال تصویر به Gemini...")

        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=data,
            timeout=120
        )

        print(
            f"🖼️ Gemini Image Status: "
            f"{response.status_code}"
        )

        print(
            f"📦 Response Length: "
            f"{len(response.text)}"
        )

        if response.status_code == 200:

            result = response.json()

            candidates = result.get(
                "candidates",
                []
            )

            if not candidates:

                print(
                    "❌ Gemini برای تصویر "
                    "candidate برنگرداند."
                )

                print(result)

                return (
                    "❌ نتونستم تصویر رو تحلیل کنم."
                )

            content = candidates[0].get(
                "content",
                {}
            )

            parts = content.get(
                "parts",
                []
            )

            answer = ""

            for part in parts:

                if "text" in part:

                    answer += part["text"]

            if not answer:

                return (
                    "❌ Gemini پاسخی برای تصویر "
                    "ارسال نکرد."
                )

            # ------------------------------------------------
            # ذخیره پیام تصویر در حافظه
            # ------------------------------------------------

            chat_history[chat_id].append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "[تصویر ارسال شد] "
                                + user_text
                            )
                        }
                    ]
                }
            )

            # ذخیره پاسخ
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

            # محدود کردن حافظه
            if len(chat_history[chat_id]) > 20:

                chat_history[chat_id] = (
                    chat_history[chat_id][-20:]
                )

            print(
                "✅ تحلیل تصویر با موفقیت انجام شد."
            )

            return answer

        # ------------------------------
        # خطاهای تصویر
        # ------------------------------

        print("❌ Gemini Image Error:")
        print(response.text)

        if response.status_code == 400:

            return (
                "❌ Gemini نتونست درخواست تصویر "
                "رو پردازش کنه.\n"
                "فرمت یا حجم تصویر رو بررسی کن."
            )

        elif response.status_code == 403:

            return (
                "❌ دسترسی Gemini برای تحلیل "
                "تصویر رد شد.\n"
                "API Key رو بررسی کن."
            )

        elif response.status_code == 429:

            return (
                "⏳ درخواست‌های Gemini بیش از حد مجاز شده.\n"
                "لطفاً کمی بعد دوباره امتحان کن."
            )

        elif response.status_code == 503:

            return (
                "⏳ سرویس Gemini فعلاً شلوغ است.\n"
                "چند لحظه بعد دوباره امتحان کن."
            )

        else:

            return (
                "❌ متأسفانه فعلاً نتونستم "
                "تصویر رو تحلیل کنم.\n"
                "چند لحظه دیگه دوباره امتحان کن."
            )

    except requests.exceptions.Timeout:

        print(
            "❌ تحلیل تصویر Timeout شد."
        )

        return (
            "⏳ تحلیل تصویر خیلی طول کشید.\n"
            "لطفاً دوباره امتحان کن."
        )

    except requests.exceptions.RequestException as e:

        print(
            "❌ خطای ارتباط تصویر با Gemini:"
        )

        print(e)

        return (
            "❌ ارتباط با Gemini برای "
            "تحلیل تصویر برقرار نشد."
        )

    except Exception as e:

        print(
            "❌ خطای ناشناخته در تحلیل تصویر:"
        )

        print(e)

        return (
            "❌ هنگام تحلیل تصویر مشکلی پیش آمد."
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
            "✨ قابلیت تحلیل تصویر نیز "
            "به ربات اضافه شده است."
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
            "🖼️ می‌تونی عکس هم بفرستی "
            "تا تصویر رو بررسی کنم.\n\n"
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

    if not chat_id:
        return

    # ==================================================
    # متن پیام
    # ==================================================

    text = message.get(
        "text",
        ""
    ).strip()

    # ==================================================
    # /start
    # ==================================================

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

    # ==================================================
    # /stop
    # ==================================================

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

    # ==================================================
    # دریافت عکس
    # ==================================================

    if "photo" in message:

        print("========================================")
        print("🖼️ عکس دریافت شد")
        print(f"👤 Chat ID: {chat_id}")
        print("========================================")

        # فقط در حالت AI
        if chat_id not in ai_users:

            send_message(
                chat_id,

                "🖼️ عکس دریافت شد!\n\n"
                "اول گزینه «🧠 هوش مصنوعی» "
                "رو فعال کن، بعد عکست رو بفرست."
            )

            return

        photos = message.get(
            "photo",
            []
        )

        if not photos:

            send_message(
                chat_id,
                "❌ نتونستم اطلاعات عکس رو دریافت کنم."
            )

            return

        # Telegram چند سایز از عکس می‌فرستد
        # آخرین مورد معمولاً بزرگ‌ترین سایز است
        largest_photo = photos[-1]

        file_id = largest_photo.get(
            "file_id"
        )

        if not file_id:

            send_message(
                chat_id,
                "❌ شناسه عکس پیدا نشد."
            )

            return

                # کپشن عکس
        caption = message.get(
            "caption",
            ""
        ).strip()

        if not caption:
            caption = (
                "این تصویر را با دقت بررسی کن "
                "و درباره آن توضیح بده."
            )

        print(
            f"📝 Caption: {caption}"
        )

        # ==================================================
        # پیام «دارم بررسی می‌کنم»
        # ==================================================

        thinking_response = send_message(
            chat_id,
            "🖼️ دارم تصویر رو بررسی می‌کنم..."
        )

        thinking_message_id = None

        if thinking_response:
            if thinking_response.get("ok"):
                thinking_message_id = (
                    thinking_response
                    .get("result", {})
                    .get("message_id")
                )

        # ==================================================
        # دریافت اطلاعات فایل از Telegram
        # ==================================================

        file_path = get_telegram_file(
            file_id
        )

        if not file_path:

            answer = (
                "❌ نتونستم اطلاعات عکس رو "
                "از تلگرام دریافت کنم."
            )

        else:

            print(
                f"📁 Telegram File Path: {file_path}"
            )

            # ==================================================
            # دانلود عکس
            # ==================================================

            image_bytes = download_telegram_file(
                file_path
            )

            if not image_bytes:

                answer = (
                    "❌ نتونستم عکس رو "
                    "از تلگرام دانلود کنم."
                )

            else:

                print(
                    f"📦 حجم عکس: "
                    f"{len(image_bytes)} bytes"
                )

                # ==================================================
                # تشخیص نوع تصویر
                # ==================================================

                mime_type = get_image_mime_type(
                    file_path
                )

                print(
                    f"🖼️ MIME Type: {mime_type}"
                )

                # ==================================================
                # ارسال تصویر به Gemini
                # ==================================================

                answer = ask_gemini_image(
                    chat_id,
                    image_bytes,
                    mime_type,
                    caption
                )

        # ==================================================
        # ارسال پاسخ Gemini
        # ==================================================

        send_message(
            chat_id,
            answer
        )

        # ==================================================
        # حذف پیام در حال بررسی
        # ==================================================

        if thinking_message_id:

            delete_message(
                chat_id,
                thinking_message_id
            )

        print(
            "✅ پردازش تصویر تمام شد."
        )

        return

    # ==================================================
    # حالت هوش مصنوعی - پیام متنی
    # ==================================================

    if chat_id in ai_users:

        print("========================================")
        print("🧠 کاربر در حالت هوش مصنوعی است.")
        print(f"👤 Chat ID: {chat_id}")
        print(f"💬 Text: {text}")
        print("========================================")

        if not text:
            return

        # ==================================================
        # پیام در حال فکر کردن
        # ==================================================

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

        # ==================================================
        # ارسال متن به Gemini
        # ==================================================

        answer = ask_gemini(
            chat_id,
            text
        )

        # ==================================================
        # ارسال جواب
        # ==================================================

        send_message(
            chat_id,
            answer
        )

        # ==================================================
        # حذف پیام «دارم فکر می‌کنم»
        # ==================================================

        if thinking_message_id:

            delete_message(
                chat_id,
                thinking_message_id
            )

        print(
            "✅ پردازش پیام متنی تمام شد."
        )

        return

    # ==================================================
    # پیام ناشناخته
    # ==================================================

    send_message(
        chat_id,
        "🤔 متوجه نشدم.\n\n"
        "برای شروع دوباره /start رو بفرست."
    )


# ==================================================
# دریافت پیام‌های Telegram
# ==================================================

def telegram_bot():

    global offset

    print("🤖 ربات تلگرام روشن شد!")

    # ==================================================
    # تست اتصال به Telegram
    # ==================================================

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getMe",
            timeout=30
        )

        result = response.json()

        if result.get("ok"):

            username = (
                result["result"]
                .get("username")
            )

            print(
                f"✅ اتصال به Telegram موفق بود: "
                f"@{username}"
            )

        else:

            print(
                "❌ اتصال به Telegram ناموفق:"
            )

            print(result)

    except Exception as e:

        print(
            "❌ خطا در اتصال به Telegram:"
        )

        print(e)

    # ==================================================
    # حلقه دریافت پیام
    # ==================================================

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

            for update in updates:

                offset = (
                    update["update_id"] + 1
                )

                # ==================================================
                # Callback Query
                # ==================================================

                if "callback_query" in update:

                    handle_callback(
                        update
                    )

                    continue

                # ==================================================
                # Message
                # ==================================================

                if "message" in update:

                    handle_message(
                        update["message"]
                    )

        except requests.exceptions.Timeout:

            print(
                "⏳ Telegram Timeout..."
            )

            continue

        except Exception as e:

            print(
                "❌ خطای کلی ربات:"
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

    # ==================================================
    # اجرای Flask برای Render
    # ==================================================

    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    # ==================================================
    # اجرای ربات Telegram
    # ==================================================

    telegram_bot()
        
