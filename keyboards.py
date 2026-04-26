from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_age_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("✅ YES"), KeyboardButton("❌ NO"))
    return kb

def get_gender_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(KeyboardButton("👨 Male"), KeyboardButton("👩 Female"))
    return kb

def get_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("❓ How to use"), KeyboardButton("🎬 See Demo"))
    return kb

def get_dynamic_keyboard(user_id):
    from database import db
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("📥 Download APK"), KeyboardButton("🎬 See Demo"))
    kb.add(KeyboardButton("❓ How to use"))
    if db.is_admin(user_id):
        kb.add(KeyboardButton("👑 Admin Panel"))
    return kb

def get_admin_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🎬 Welcome Videos"), KeyboardButton("🎥 Demo Videos"), KeyboardButton("📦 APK Manager"), KeyboardButton("❓ How-to Content"), KeyboardButton("📢 Broadcast"), KeyboardButton("👑 Manage Admins"), KeyboardButton("📊 Stats"), KeyboardButton("👥 User Records"), KeyboardButton("🚫 Ban Management"), KeyboardButton("🔑 Login Keys"), KeyboardButton("👤 Temp Admins"), KeyboardButton("🖥️ System"), KeyboardButton("🔑 Change Password"), KeyboardButton("🚪 Logout"), KeyboardButton("🚪 Exit Admin"))
    return kb

def get_ban_management_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🚫 Ban User"), KeyboardButton("✅ Unban User"), KeyboardButton("📋 Banned Users List"), KeyboardButton("🔍 Search Banned User"), KeyboardButton("🔙 Back"))
    return kb

def get_login_keys_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("➕ Generate Key"), KeyboardButton("📋 List Keys"), KeyboardButton("🗑️ Revoke Key"), KeyboardButton("🔙 Back"))
    return kb

def get_temp_admins_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("📋 Active Sessions"), KeyboardButton("📊 Temp Admin Stats"), KeyboardButton("🗑️ Terminate Session"), KeyboardButton("🔙 Back"))
    return kb

def get_howto_content_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("🎬 Set How-to Video"), KeyboardButton("🗑️ Delete How-to Video"), KeyboardButton("📝 Set How-to Text"), KeyboardButton("🗑️ Delete How-to Text"), KeyboardButton("👁️ Preview How-to"), KeyboardButton("🔙 Back"))
    return kb

def get_admin_videos_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("➕ Add Welcome Video"), KeyboardButton("➕ Add Demo Video"), KeyboardButton("📋 List Welcome Videos"), KeyboardButton("📋 List Demo Videos"), KeyboardButton("🔙 Back"))
    return kb

def get_apk_manager_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("➕ Add APK"), KeyboardButton("📋 View APKs"), KeyboardButton("🔙 Back"))
    return kb

def get_manage_admin_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("➕ Add Admin"), KeyboardButton("🗑️ Remove Admin"), KeyboardButton("🔙 Back"))
    return kb

def get_user_records_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(KeyboardButton("📊 User Statistics"), KeyboardButton("🔍 Search User"), KeyboardButton("📋 All Users"), KeyboardButton("📈 Activity Report"), KeyboardButton("🔙 Back"))
    return kb

def get_back_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🔙 Back"))
    return kb

def get_broadcast_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Cancel Broadcast"))
    return kb

def get_temp_admin_info_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔄 Extend Session", callback_data="extend_session"), InlineKeyboardButton("🚪 Logout", callback_data="logout_session"))
    return kb

def get_terminate_session_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"🗑️ Terminate", callback_data=f"terminate_{user_id}"))
    return kb

def get_revoke_key_keyboard(key):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(f"🗑️ Revoke", callback_data=f"revoke_key_{key}"))
    return kb
