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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# مدل اصلی
TEXT_MODEL = "minimax/minimax-m3:free"
VISION_MODEL = "minimax/minimax-m3:free"

# مدل‌های جایگزین
TEXT_FALLBACK_MODELS = [
    TEXT_MODEL,
    "nvidia/nemotron-3-ultra:free",
    "openrouter/free"
]

VISION_FALLBACK_MODELS = [
    VISION_MODEL,
    "nvidia/nemotron-3-ultra:free",
    "openrouter/free"
]

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
)

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

# ===================================
# حافظه موقت
# ===================================

chat_history = {}

# کاربران فعال
ai_users = set()

# offset تلگرام
offset = 0


# ===================================
# ارسال پیام Telegram
# ===================================

def send_message(chat_id, text):

    start_time = time.time()

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

            print(
                "❌ Telegram Send Error:",
                response.status_code
            )

            return None

        print(
            "⏱️ Telegram send time:",
            round(
                time.time() - start_time,
                2
            ),
            "seconds"
        )

        return response.json()

    except Exception as e:

        print(
            "❌ Telegram Send Error:",
            e
        )

        return None


# ===================================
# درخواست متنی به OpenRouter
# با سیستم Fallback
# ===================================

def ask_bai(chat_id, text):

    print("\n==============================")
    print("🧠 درخواست OpenRouter")
    print("👤 Chat:", chat_id)
    print("💬 Text:", text)

    if chat_id not in chat_history:

        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "content": text
    })

    history = chat_history[chat_id][-10:]

    headers = {
        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),
        "Content-Type": "application/json",
        "HTTP-Referer": (
            "https://github.com/"
            "jajshaja/telegram-ai-bot"
        ),
        "X-Title": "Telegram AI Bot"
    }

    for model in TEXT_FALLBACK_MODELS:

        print(
            "\n📡 امتحان مدل:",
            model
        )

        data = {
            "model": model,
            "messages": history,
            "stream": False
        }

        try:

            start_time = time.time()

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=data,
                timeout=120
            )

            elapsed = round(
                time.time() - start_time,
                2
            )

            print(
                "⏱️ زمان پاسخ:",
                elapsed,
                "ثانیه"
            )

            print(
                "OpenRouter Status:",
                response.status_code
            )

            # =================================
            # موفق
            # =================================

            if response.status_code == 200:

                result = response.json()

                choices = result.get(
                    "choices",
                    []
                )

                if not choices:

                    print(
                        "⚠️ مدل پاسخ خالی داد."
                    )

                    continue

                message = choices[0].get(
                    "message",
                    {}
                )

                answer = message.get(
                    "content",
                    ""
                )

                if not answer:

                    print(
                        "⚠️ پاسخ مدل خالی بود."
                    )

                    continue

                answer = answer.strip()

                chat_history[chat_id].append({
                    "role": "assistant",
                    "content": answer
                })

                chat_history[chat_id] = (
                    chat_history[chat_id][-20:]
                )

                print(
                    "✅ مدل موفق:",
                    model
                )

                print(
                    "✅ پاسخ OpenRouter دریافت شد."
                )

                return answer

            # =================================
            # Rate Limit
            # =================================

            elif response.status_code == 429:

                print(
                    "⚠️ Rate Limit مدل:",
                    model
                )

                continue

            # =================================
            # خطاهای سرور
            # =================================

            elif response.status_code >= 500:

                print(
                    "⚠️ خطای سرور مدل:",
                    model,
                    response.status_code
                )

                continue

            # =================================
            # سایر خطاها
            # =================================

            else:

                print(
                    "⚠️ مدل پاسخ ناموفق داد:",
                    model
                )

                print(
                    response.text[:300]
                )

                continue

        except Exception as e:

            print(
                "⚠️ خطا در مدل:",
                model
            )

            print(
                "جزئیات:",
                e
            )

            continue

    # ===================================
    # همه مدل‌ها شکست خوردند
    # ===================================

    print(
        "❌ تمام مدل‌های متنی شکست خوردند."
    )

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

            print(
                "❌ getFile Error:",
                response.status_code
            )

            return None

        result = response.json()

        if result.get("ok"):

            return result["result"]["file_path"]

        return None

    except Exception as e:

        print(
            "❌ خطای getFile:",
            e
        )

        return None


# ===================================
# دانلود فایل
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

        print(
            "❌ خطای دانلود:",
            e
        )

        return None


# ===================================
# تحلیل تصویر با OpenRouter
# با سیستم Fallback
# ===================================

def ask_bai_image(
    chat_id,
    image_bytes,
    caption=""
):

    print("\n==============================")
    print("🖼️ تحلیل تصویر")
    print("👤 Chat:", chat_id)
    print(
        "📏 Size:",
        len(image_bytes)
    )

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

    headers = {

        "Authorization": (
            f"Bearer {OPENROUTER_API_KEY}"
        ),

        "Content-Type": "application/json",

        "HTTP-Referer": (
            "https://github.com/"
            "jajshaja/telegram-ai-bot"
        ),

        "X-Title": "Telegram AI Bot"
    }

    # ===================================
    # امتحان مدل‌های Vision
    # ===================================

    for model in VISION_FALLBACK_MODELS:

        print(
            "\n📡 امتحان Vision مدل:",
            model
        )

        data = {

            "model": model,

            "messages": history + [
                current_message
            ],

            "stream": False
        }

        try:

            start_time = time.time()

            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=data,
                timeout=180
            )

            elapsed = round(
                time.time() - start_time,
                2
            )

            print(
                "⏱️ زمان تحلیل:",
                elapsed,
                "ثانیه"
            )

            print(
                "OpenRouter Image Status:",
                response.status_code
            )

            # =================================
            # موفق
            # =================================

            if response.status_code == 200:

                result = response.json()

                choices = result.get(
                    "choices",
                    []
                )

                if not choices:

                    print(
                        "⚠️ مدل Vision پاسخ نداد."
                    )

                    continue

                message = choices[0].get(
                    "message",
                    {}
                )

                answer = message.get(
                    "content",
                    ""
                )

                if not answer:

                    print(
                        "⚠️ پاسخ Vision خالی بود."
                    )

                    continue

                answer = answer.strip()

                # ذخیره نسخه متنی تصویر
                if chat_id not in chat_history:

                    chat_history[chat_id] = []

                chat_history[chat_id].append({

                    "role": "user",

                    "content": (
                        "[تصویر] "
                        + caption
                    )
                })

                chat_history[chat_id].append({

                    "role": "assistant",

                    "content": answer
                })

                chat_history[chat_id] = (
                    chat_history[chat_id][-20:]
                )

                print(
                    "✅ Vision مدل موفق:",
                    model
                )

                print(
                    "✅ تصویر با موفقیت تحلیل شد."
                )

                return answer

            # =================================
            # Rate Limit
            # =================================

            elif response.status_code == 429:

                print(
                    "⚠️ Vision Rate Limit:",
                    model
                )

                continue

            # =================================
            # خطاهای سرور
            # =================================

            elif response.status_code >= 500:

                print(
                    "⚠️ Vision Server Error:",
                    model,
                    response.status_code
                )

                continue

            # =================================
            # سایر خطاها
            # =================================

            else:

                print(
                    "⚠️ Vision مدل ناموفق:",
                    model
                )

                print(
                    response.text[:300]
                )

                continue

        except Exception as e:

            print(
                "⚠️ خطا در Vision مدل:",
                model
            )

            print(
                "جزئیات:",
                e
            )

            continue

    # ===================================
    # همه مدل‌های Vision شکست خوردند
    # ===================================

    print(
        "❌ تمام مدل‌های Vision شکست خوردند."
    )

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

        # =================================
        # اگر جواب گرفتیم
        # =================================

        if answer:

            send_message(
                chat_id,
                answer
            )

        # =================================
        # هیچ مدلی جواب نداد
        # =================================

        else:

            send_message(
                chat_id,
                "❌ هوش مصنوعی فعلاً پاسخی نداد."
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

        # اگر جواب گرفتیم
        if answer:

            send_message(
                chat_id,
                answer
            )

        # اگر هیچ مدل جواب نداد
        else:

            send_message(
                chat_id,
                "❌ هوش مصنوعی فعلاً پاسخی نداد."
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
                "⚠️ نتونستم آپدیت‌های قدیمی "
                "رو بررسی کنم."
            )

            return

        result = response.json()

        updates = result.get(
            "result",
            []
        )

        if updates:

            offset = (
                updates[-1]["update_id"] + 1
            )

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
    "🧠 OpenRouter Text:",
    TEXT_MODEL
)

print(
    "🖼️ OpenRouter Vision:",
    VISION_MODEL
)

print(
    "🔄 Fallback:",
    "فعال"
)

print(
    "==================================="
)


# ===================================
# بررسی کلیدها
# ===================================

if (
    not TELEGRAM_TOKEN
    or TELEGRAM_TOKEN.startswith("اینجا_")
):

    print(
        "❌ TELEGRAM_TOKEN تنظیم نشده."
    )

    raise SystemExit


if (
    not OPENROUTER_API_KEY
    or OPENROUTER_API_KEY.startswith("اینجا_")
):

    print(
        "❌ OPENROUTER_API_KEY تنظیم نشده."
    )

    raise SystemExit


# ===================================
# تست Telegram
# ===================================

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


# ===================================
# پاکسازی آپدیت‌های قدیمی
# ===================================

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

            # =================================
            # پیام معمولی
            # =================================

            message = update.get(
                "message"
            )

            if message:

                handle_message(
                    message
                )

            # =================================
            # Callback Query
            # =================================

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
                            "قدرت گرفته از OpenRouter"
                        )

                # =================================
                # پاسخ به Callback
                # =================================

                try:

                    requests.post(
                        f"{TELEGRAM_URL}/"
                        "answerCallbackQuery",

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
