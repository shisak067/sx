import time
import threading
import psutil
from datetime import datetime, timedelta
from telebot.types import Message

from config import logger, CPU_ALERT_THRESHOLD, CHECK_INTERVAL, MESSAGE_DELAY, SOURCE_CHANNEL_ID, APK_MESSAGE_ID
from database import db
from keyboards import get_main_keyboard, get_dynamic_keyboard, get_howto_content_keyboard

# Rate limiting
last_message_time = {}

def rate_limit(user_id: int) -> bool:
    current_time = time.time()
    if user_id in last_message_time:
        if current_time - last_message_time[user_id] < 0.1:
            return False
    last_message_time[user_id] = current_time
    return True

def forward_apk(chat_id: int):
    apk_messages = db.get_all_apk_messages()
    if not apk_messages:
        try:
            from main import bot
            bot.copy_message(chat_id=chat_id, from_chat_id=SOURCE_CHANNEL_ID, message_id=APK_MESSAGE_ID)
            return True
        except Exception as e:
            logger.error(f"APK forward failed: {e}")
            return False
    for apk in apk_messages:
        try:
            from main import bot
            bot.copy_message(chat_id=chat_id, from_chat_id=apk["channel_id"], message_id=apk["message_id"])
            time.sleep(MESSAGE_DELAY)
        except Exception as e:
            logger.error(f"Failed to forward APK: {e}")
    return True

def send_welcome_flow(chat_id: int, user_name: str):
    from main import bot
    for video in db.get_all_welcome_videos():
        caption = video.get("caption", "").replace("{name}", user_name) if video.get("caption") else ""
        try:
            if caption:
                bot.send_video(chat_id, video["video_file_id"], caption=caption)
            else:
                bot.send_video(chat_id, video["video_file_id"])
            time.sleep(MESSAGE_DELAY)
        except:
            pass
    forward_apk(chat_id)
    bot.send_message(chat_id, "Need help? Tap below to see how to use the app! 🎉", reply_markup=get_main_keyboard())
    time.sleep(MESSAGE_DELAY)
    bot.send_message(chat_id, "Watch the demo here 👇🏻👈🏻")
    time.sleep(MESSAGE_DELAY)
    bot.send_message(chat_id, "📧 Options 📧", reply_markup=get_dynamic_keyboard(chat_id))

def send_how_to_use(chat_id: int, is_admin: bool = False):
    from main import bot
    if not is_admin:
        howto_text = db.get_howto_text()
        if howto_text:
            bot.send_message(chat_id, f"📖 **How to Use**\n\n{howto_text['text']}", parse_mode="Markdown")
        video = db.get_howto_video()
        if video:
            bot.send_video(chat_id, video["video_file_id"], caption="🎥 **Video Tutorial**\n\nWatch this step-by-step guide!", parse_mode="Markdown")
        if not db.has_howto_content():
            bot.send_message(chat_id, "⚠️ No tutorial available yet. Please check back later or contact support for assistance.")
        return
    text_content = db.get_howto_text()
    video_content = db.get_howto_video()
    info_text = "📖 **HOW TO USE - Admin View**\n\n━━━━━━━━━━━━━━━━━━━━\n📝 **Text Instructions:**\n"
    if text_content:
        info_text += f"✅ Current Text: {text_content['text'][:200]}...\n🕐 Last updated: {text_content['updated_at'].strftime('%Y-%m-%d %H:%M')}\n"
    else:
        info_text += "❌ No text instructions set\n"
    info_text += "━━━━━━━━━━━━━━━━━━━━\n🎥 **Video Tutorial:**\n"
    if video_content:
        info_text += f"✅ Video available\n🕐 Added on: {video_content['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
    else:
        info_text += "❌ No video tutorial set\n"
    info_text += "━━━━━━━━━━━━━━━━━━━━\n🔧 Use the buttons below to manage content"
    bot.send_message(chat_id, info_text, parse_mode="Markdown", reply_markup=get_howto_content_keyboard())
    if video_content:
        bot.send_video(chat_id, video_content["video_file_id"], caption="🎥 **Current Video Tutorial**\n\nThis is what users will see", parse_mode="Markdown")

# CPU Monitor
last_cpu_alert_time = {}

def check_cpu_and_alert():
    global last_cpu_alert_time
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent >= CPU_ALERT_THRESHOLD:
            for admin in db.get_all_admins():
                admin_id = admin["user_id"]
                last_alert = last_cpu_alert_time.get(admin_id, 0)
                if time.time() - last_alert > 600:
                    try:
                        from main import bot
                        bot.send_message(admin_id, f"⚠️ CPU Alert: {cpu_percent}%")
                        last_cpu_alert_time[admin_id] = time.time()
                    except:
                        pass
    except:
        pass

def start_cpu_monitor():
    def monitor():
        while True:
            check_cpu_and_alert()
            time.sleep(CHECK_INTERVAL)
    threading.Thread(target=monitor, daemon=True).start()

def start_cleanup_task():
    def cleaner():
        while True:
            try:
                count = db.cleanup_expired()
                if count > 0:
                    logger.info(f"Cleaned up {count} expired sessions/keys")
            except:
                pass
            time.sleep(300)
    threading.Thread(target=cleaner, daemon=True).start()

# Admin required decorator
def admin_required(func):
    from functools import wraps
    @wraps(func)
    def wrapper(message: Message):
        from main import bot
        if not db.is_admin(message.from_user.id):
            bot.reply_to(message, "❌ You are not authorized to use this command.")
            return
        return func(message)
    return wrapper
