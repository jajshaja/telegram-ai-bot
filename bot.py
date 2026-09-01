import requests
import os
import base64
import time
from dotenv import load_dotenv

load_dotenv()

# ===================================
# تنظیمات
# ===================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
BAI_API_KEY = os.getenv("BAI_API_KEY")

TEXT_MODEL = "deepseek-v4-flash"
VISION_MODEL = "deepseek-v4-flash-vision-exp"

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
BAI_URL = "https://api.b.ai/v1/chat/completions"

# حافظه موقت
chat_history = {}

# کاربران فعال
ai_users = set()

# offset تلگرام
offset = 0


# ===================================
# ارسال پیام Telegram
# ===================================

def send_message(chat_id, text):

    try:
        response = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=30
        )

        if response.status_code != 200:
            print("❌ Telegram Send Error:", response.status_code)
            return None

        return response.json()

    except Exception as e:
        print("❌ Telegram Send Error:", e)
        return None


# ===================================
# درخواست متنی به B.AI
# ===================================

def ask_bai(chat_id, text):

    print("\n==============================")
    print("🧠 درخواست B.AI")
    print("👤 Chat:", chat_id)
    print("💬 Text:", text)
    print("📡 ارسال به B.AI...")

    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "content": text
    })

    history = chat_history[chat_id][-10:]

    data = {
        "model": TEXT_MODEL,
        "messages": history,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {BAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            BAI_URL,
            headers=headers,
            json=data,
            timeout=120
        )

        print("B.AI Status:", response.status_code)

        if response.status_code != 200:
            print("❌ B.AI Error:", response.text[:500])
            return None

        result = response.json()

        choices = result.get("choices", [])

        if not choices:
            print("❌ B.AI پاسخ نداد.")
            return None

        message = choices[0].get("message", {})

        answer = message.get("content", "")

        if not answer:
            print("❌ پاسخ B.AI خالی بود.")
            return None

        answer = answer.strip()

        chat_history[chat_id].append({
            "role": "assistant",
            "content": answer
        })

        chat_history[chat_id] = chat_history[chat_id][-20:]

        print("✅ پاسخ B.AI دریافت شد.")

        return answer

    except Exception as e:

        print("❌ خطای B.AI:", e)

        return None


# ===================================
# دریافت فایل Telegram
# ===================================

def get_telegram_file(file_id):

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getFile",
            params={
                "file_id": file_id
            },
            timeout=30
        )

        if response.status_code != 200:
            print("❌ getFile Error:", response.status_code)
            return None

        result = response.json()

        if result.get("ok"):
            return result["result"]["file_path"]

        return None

    except Exception as e:

        print("❌ خطای getFile:", e)

        return None


# ===================================
# دانلود عکس
# ===================================

def download_file(file_path):

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

        if response.status_code == 200:

            print(
                "📥 عکس دریافت شد:",
                len(response.content),
                "bytes"
            )

            return response.content

        print(
            "❌ Download Error:",
            response.status_code
        )

        return None

    except Exception as e:

        print("❌ خطای دانلود:", e)

        return None


# ===================================
# تحلیل تصویر با B.AI
# ===================================

def ask_bai_image(
    chat_id,
    image_bytes,
    caption=""
):

    print("\n==============================")
    print("🖼️ تحلیل تصویر")
    print("👤 Chat:", chat_id)
    print("📏 Size:", len(image_bytes))
    print("📡 ارسال تصویر به B.AI...")

    if not caption:

        caption = (
            "این تصویر را با دقت بررسی کن "
            "و توضیح بده چه چیزی در آن می‌بینی."
        )

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    # تاریخچه متنی قبلی
    history = chat_history.get(
        chat_id,
        []
    )[-8:]

    current_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": caption
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": (
                        "data:image/jpeg;base64,"
                        + image_base64
                    )
                }
            }
        ]
    }

    data = {
        "model": VISION_MODEL,
        "messages": history + [
            current_message
        ],
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {BAI_API_KEY}",
        "Content-Type": "application/json"
    }

    try:

        response = requests.post(
            BAI_URL,
            headers=headers,
            json=data,
            timeout=180
        )

        print(
            "B.AI Image Status:",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "❌ B.AI Image Error:",
                response.text[:500]
            )

            return None

        result = response.json()

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            print("❌ B.AI برای تصویر پاسخ نداد.")

            return None

        message = choices[0].get(
            "message",
            {}
        )

        answer = message.get(
            "content",
            ""
        )

        if not answer:

            print("❌ پاسخ تصویر خالی بود.")

            return None

        answer = answer.strip()

        # ذخیره نسخه متنی تصویر در حافظه
        if chat_id not in chat_history:
            chat_history[chat_id] = []

        chat_history[chat_id].append({
            "role": "user",
            "content": "[تصویر] " + caption
        })

        chat_history[chat_id].append({
            "role": "assistant",
            "content": answer
        })

        chat_history[chat_id] = \
            chat_history[chat_id][-20:]

        print("✅ تصویر با موفقیت تحلیل شد.")

        return answer

    except Exception as e:

        print("❌ خطای تحلیل تصویر:", e)

        return None


# ===================================
# پردازش پیام
# ===================================

def handle_message(message):

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

    if not chat_id:
        return

    # =================================
    # متن پیام
    # =================================

    text = message.get(
        "text",
        ""
    ).strip()

    # =================================
    # /start
    # =================================

    if text == "/start":

        ai_users.add(chat_id)

        print(
            "▶️ کاربر فعال شد:",
            chat_id
        )

        send_message(
            chat_id,
            "🤖 ربات آماده است!\n\n"
            "متنت رو بفرست یا یک عکس ارسال کن."
        )

        return

    # =================================
    # /stop
    # =================================

    if text == "/stop":

        ai_users.discard(chat_id)

        chat_history.pop(
            chat_id,
            None
        )

        print(
            "⏹️ کاربر غیرفعال شد:",
            chat_id
        )

        send_message(
            chat_id,
            "🛑 هوش مصنوعی خاموش شد."
        )

        return

    # =================================
    # بررسی فعال بودن
    # =================================

    if chat_id not in ai_users:

        send_message(
            chat_id,
            "اول /start رو بزن."
        )

        return

    # =================================
    # عکس
    # =================================

    if "photo" in message:

        print(
            "\n📸 عکس دریافت شد."
        )

        photos = message.get(
            "photo",
            []
        )

        if not photos:

            send_message(
                chat_id,
                "❌ اطلاعات عکس پیدا نشد."
            )

            return

        # بزرگ‌ترین نسخه عکس
        largest_photo = photos[-1]

        file_id = largest_photo.get(
            "file_id"
        )

        if not file_id:

            send_message(
                chat_id,
                "❌ file_id پیدا نشد."
            )

            return

        file_path = get_telegram_file(
            file_id
        )

        if not file_path:

            send_message(
                chat_id,
                "❌ نتونستم عکس رو دریافت کنم."
            )

            return

        image_bytes = download_file(
            file_path
        )

        if not image_bytes:

            send_message(
                chat_id,
                "❌ دانلود عکس ناموفق بود."
            )

            return

        caption = message.get(
            "caption",
            ""
        ).strip()

        answer = ask_bai_image(
            chat_id,
            image_bytes,
            caption
        )

        # فقط اگر واقعاً جواب گرفتیم ارسال کن
        if answer:

            send_message(
                chat_id,
                answer
            )

        else:

            send_message(
                chat_id,
                "❌ B.AI فعلاً نتونست تصویر رو پاسخ بده."
            )

        return

    # =================================
    # پیام متنی
    # =================================

    if text:

        answer = ask_bai(
            chat_id,
            text
        )

        # اگر B.AI جواب داد، همان جواب ارسال شود
        if answer:

            send_message(
                chat_id,
                answer
            )

        else:

            send_message(
                chat_id,
                "❌ B.AI فعلاً پاسخ نداد."
            )


# ===================================
# دریافت آپدیت Telegram
# ===================================

def get_updates():

    global offset

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getUpdates",
            params={
                "offset": offset,
                "timeout": 30
            },
            timeout=40
        )

        if response.status_code != 200:

            print(
                "❌ Telegram getUpdates:",
                response.status_code
            )

            return []

        result = response.json()

        if not result.get("ok"):

            print(
                "❌ Telegram Error:",
                result
            )

            return []

        return result.get(
            "result",
            []
        )

    except Exception as e:

        print(
            "❌ getUpdates Error:",
            e
        )

        return []


# ===================================
# پاک کردن آپدیت‌های قدیمی
# ===================================

def clear_old_updates():

    global offset

    print(
        "🧹 بررسی آپدیت‌های قدیمی..."
    )

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getUpdates",
            params={
                "offset": -1,
                "timeout": 1
            },
            timeout=10
        )

        if response.status_code != 200:
            print(
                "⚠️ نتونستم آپدیت‌های قدیمی رو بررسی کنم."
            )
            return

        result = response.json()

        updates = result.get(
            "result",
            []
        )

        if updates:

            offset = updates[-1]["update_id"] + 1

            print(
                "🗑️ آپدیت‌های قدیمی پاک شدند."
            )

        else:

            print(
                "✅ آپدیت قدیمی وجود ندارد"
            )

    except Exception as e:

        print(
            "⚠️ خطا در پاکسازی:",
            e
        )


# ===================================
# شروع ربات
# ===================================

print(
    "==================================="
)

print(
    "🤖 Telegram AI Bot Started"
)

print(
    "🧠 B.AI Text:",
    TEXT_MODEL
)

print(
    "🖼️ B.AI Vision:",
    VISION_MODEL
)

print(
    "==================================="
)

# بررسی کلیدها
if (
    not TELEGRAM_TOKEN
    or TELEGRAM_TOKEN.startswith("اینجا_")
):

    print(
        "❌ TELEGRAM_TOKEN تنظیم نشده."
    )

    raise SystemExit


if (
    not BAI_API_KEY
    or BAI_API_KEY.startswith("اینجا_")
):

    print(
        "❌ BAI_API_KEY تنظیم نشده."
    )

    raise SystemExit


# تست Telegram
try:

    response = requests.get(
        f"{TELEGRAM_URL}/getMe",
        timeout=15
    )

    if response.status_code == 200:

        bot_info = response.json()

        if bot_info.get("ok"):

            print(
                "✅ Telegram OK"
            )

        else:

            print(
                "❌ Telegram Token نامعتبر است."
            )

    else:

        print(
            "❌ Telegram:",
            response.status_code
        )

except Exception as e:

    print(
        "❌ Telegram Connection Error:",
        e
    )


clear_old_updates()

print(
    "🟢 ربات آماده دریافت پیام جدید است."
)

# ===================================
# حلقه اصلی
# ===================================

while True:

    try:

        updates = get_updates()

        for update in updates:

            offset = (
                update["update_id"] + 1
            )

            message = update.get(
                "message"
            )

            if message:

                handle_message(
                    message
                )

            # callback query
            callback = update.get(
                "callback_query"
            )

            if callback:

                chat = callback.get(
                    "message",
                    {}
                ).get(
                    "chat",
                    {}
                )

                chat_id = chat.get(
                    "id"
                )

                data = callback.get(
                    "data"
                )

                if chat_id:

                    if data == "ai":

                        ai_users.add(
                            chat_id
                        )

                        print(
                            "▶️ کاربر فعال شد:",
                            chat_id
                        )

                        send_message(
                            chat_id,
                            "🧠 هوش مصنوعی فعال شد!\n\n"
                            "پیامت رو بفرست."
                        )

                    elif data == "about":

                        send_message(
                            chat_id,
                            "🤖 ربات هوش مصنوعی\n\n"
                            "قدرت گرفته از B.AI"
                        )

                    # پاسخ به callback
                    try:

                        requests.post(
                            f"{TELEGRAM_URL}/answerCallbackQuery",
                            json={
                                "callback_query_id":
                                    callback.get("id")
                            },
                            timeout=10
                        )

                    except Exception:
                        pass

    except KeyboardInterrupt:

        print(
            "\n🛑 ربات متوقف شد."
        )

        break

    except Exception as e:

        print(
            "❌ خطای اصلی:",
            e
        )

        time.sleep(3)
