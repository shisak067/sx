import secrets
import string
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from bson.objectid import ObjectId
from pymongo import MongoClient
from cachetools import TTLCache

from config import logger, MONGO_URI, MONGO_DB_NAME, OWNER_ID, DEFAULT_ADMIN_PASSWORD, DEFAULT_TEMP_ADMIN_TIMEOUT

# Cache Manager
class CacheManager:
    def __init__(self):
        self.user_cache = TTLCache(maxsize=1000, ttl=300)
        self.admin_cache = TTLCache(maxsize=100, ttl=60)
        self.banned_cache = TTLCache(maxsize=1000, ttl=300)
        self.settings_cache = TTLCache(maxsize=50, ttl=60)
    
    def get_user(self, user_id):
        return self.user_cache.get(user_id)
    
    def set_user(self, user_id, data):
        self.user_cache[user_id] = data
    
    def invalidate_user(self, user_id):
        if user_id in self.user_cache:
            del self.user_cache[user_id]
        if user_id in self.banned_cache:
            del self.banned_cache[user_id]
    
    def is_admin_cached(self, user_id):
        return self.admin_cache.get(f"admin_{user_id}")
    
    def set_admin_cache(self, user_id, is_admin):
        self.admin_cache[f"admin_{user_id}"] = is_admin
    
    def is_banned_cached(self, user_id):
        return self.banned_cache.get(f"banned_{user_id}")
    
    def set_banned_cache(self, user_id, is_banned):
        self.banned_cache[f"banned_{user_id}"] = is_banned

cache = CacheManager()

# Database Class
class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
        
        # Collections
        self.users = self.db["users"]
        self.admins = self.db["admins"]
        self.temp_admins = self.db["temp_admins"]
        self.admin_sessions = self.db["admin_sessions"]
        self.login_keys = self.db["login_keys"]
        self.banned_users = self.db["banned_users"]
        self.welcome_videos = self.db["welcome_videos"]
        self.demo_videos = self.db["demo_videos"]
        self.howto_videos = self.db["howto_videos"]
        self.howto_texts = self.db["howto_texts"]
        self.apk_messages = self.db["apk_messages"]
        self.user_records = self.db["user_records"]
        self.user_logins = self.db["user_logins"]
        self.user_actions = self.db["user_actions"]
        self.bot_settings = self.db["bot_settings"]
        
        self.create_indexes()
        self.initialize_data()
    
    def connect(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, maxPoolSize=50)
            self.db = self.client[MONGO_DB_NAME]
            self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            time.sleep(5)
            self.connect()
    
    def create_indexes(self):
        try:
            self.users.create_index("user_id", unique=True)
            self.admins.create_index("user_id", unique=True)
            self.temp_admins.create_index("user_id", unique=True)
            self.admin_sessions.create_index([("user_id", 1), ("expires_at", 1)])
            self.admin_sessions.create_index("expires_at", expireAfterSeconds=0)
            self.login_keys.create_index([("key", 1)], unique=True)
            self.login_keys.create_index("expires_at")
            self.banned_users.create_index("user_id", unique=True)
            self.user_records.create_index("user_id", unique=True)
            self.user_records.create_index("last_active", -1)
            self.user_logins.create_index([("user_id", 1), ("login_time", -1)])
        except Exception as e:
            logger.error(f"Index creation error: {e}")
    
    def initialize_data(self):
        if self.apk_messages.count_documents({}) == 0:
            from config import APK_MESSAGE_ID, SOURCE_CHANNEL_ID
            self.apk_messages.insert_one({"message_id": APK_MESSAGE_ID, "channel_id": SOURCE_CHANNEL_ID, "name": "Main APK", "created_at": datetime.now()})
        
        if not self.admins.find_one({"user_id": OWNER_ID}):
            self.admins.insert_one({"user_id": OWNER_ID, "added_by": OWNER_ID, "added_at": datetime.now(), "is_owner": True})
        
        self.init_admin_password()
    
    def init_admin_password(self):
        setting = self.bot_settings.find_one({"key": "admin_password"})
        if not setting:
            self.bot_settings.insert_one({"key": "admin_password", "value": DEFAULT_ADMIN_PASSWORD, "updated_at": datetime.now(), "updated_by": OWNER_ID})
    
    def get_admin_password(self):
        cached = cache.settings_cache.get("admin_password")
        if cached:
            return cached
        setting = self.bot_settings.find_one({"key": "admin_password"})
        password = setting["value"] if setting else DEFAULT_ADMIN_PASSWORD
        cache.settings_cache["admin_password"] = password
        return password
    
    def set_admin_password(self, new_password: str, updated_by: int):
        self.bot_settings.update_one({"key": "admin_password"}, {"$set": {"value": new_password, "updated_at": datetime.now(), "updated_by": updated_by}}, upsert=True)
        cache.settings_cache["admin_password"] = new_password
        return True
    
    # Admin Checks
    def is_admin(self, user_id: int) -> bool:
        cached = cache.is_admin_cached(user_id)
        if cached is not None:
            return cached
        if self.admins.find_one({"user_id": user_id}):
            cache.set_admin_cache(user_id, True)
            return True
        is_temp = self.is_temp_admin(user_id)
        cache.set_admin_cache(user_id, is_temp)
        return is_temp
    
    def is_permanent_admin(self, user_id: int) -> bool:
        return self.admins.find_one({"user_id": user_id}) is not None
    
    def is_banned(self, user_id: int) -> bool:
        cached = cache.is_banned_cached(user_id)
        if cached is not None:
            return cached
        is_banned = self.banned_users.find_one({"user_id": user_id}) is not None
        cache.set_banned_cache(user_id, is_banned)
        return is_banned
    
    # Login Key Management
    def generate_login_key(self, created_by: int, max_uses: int = 1, duration_hours: int = 24, note: str = "") -> str:
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(12))
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        self.login_keys.insert_one({"key": key, "created_by": created_by, "created_at": datetime.now(), "expires_at": expires_at, "max_uses": max_uses, "used_count": 0, "is_active": True, "note": note, "users_used": []})
        return key
    
    def get_login_key_info(self, key: str):
        return self.login_keys.find_one({"key": key, "is_active": True, "expires_at": {"$gt": datetime.now()}})
    
    def use_login_key(self, key: str, user_id: int) -> bool:
        result = self.login_keys.update_one({"key": key, "is_active": True, "expires_at": {"$gt": datetime.now()}, "$expr": {"$lt": ["$used_count", "$max_uses"]}}, {"$inc": {"used_count": 1}, "$push": {"users_used": {"user_id": user_id, "used_at": datetime.now()}}})
        if result.modified_count > 0:
            key_doc = self.login_keys.find_one({"key": key})
            if key_doc and key_doc.get("used_count", 0) >= key_doc.get("max_uses", 1):
                self.login_keys.update_one({"key": key}, {"$set": {"is_active": False}})
            return True
        return False
    
    def revoke_login_key(self, key: str) -> bool:
        result = self.login_keys.delete_one({"key": key})
        return result.deleted_count > 0
    
    def get_all_login_keys(self):
        return list(self.login_keys.find({"is_active": True, "expires_at": {"$gt": datetime.now()}}))
    
    # Temp Admin Session Management
    def create_temp_admin_session(self, user_id: int, duration_seconds: int = DEFAULT_TEMP_ADMIN_TIMEOUT, used_key: str = None):
        expires_at = datetime.now() + timedelta(seconds=duration_seconds)
        self.admin_sessions.delete_many({"user_id": user_id})
        self.admin_sessions.insert_one({"user_id": user_id, "created_at": datetime.now(), "expires_at": expires_at, "is_active": True, "used_key": used_key, "login_count": 1})
        self.temp_admins.update_one({"user_id": user_id}, {"$set": {"last_login": datetime.now(), "expires_at": expires_at, "used_key": used_key}, "$setOnInsert": {"first_login": datetime.now(), "login_count": 0}, "$inc": {"login_count": 1}}, upsert=True)
        cache.set_admin_cache(user_id, True)
        return expires_at
    
    def extend_temp_admin_session(self, user_id: int, extra_seconds: int = DEFAULT_TEMP_ADMIN_TIMEOUT):
        session = self.admin_sessions.find_one({"user_id": user_id})
        if session:
            new_expiry = session["expires_at"] + timedelta(seconds=extra_seconds)
            self.admin_sessions.update_one({"user_id": user_id}, {"$set": {"expires_at": new_expiry}})
            self.temp_admins.update_one({"user_id": user_id}, {"$set": {"expires_at": new_expiry}})
            return new_expiry
        return None
    
    def is_temp_admin(self, user_id: int):
        session = self.admin_sessions.find_one({"user_id": user_id, "expires_at": {"$gt": datetime.now()}, "is_active": True})
        return session is not None
    
    def get_temp_admin_expiry(self, user_id: int):
        session = self.admin_sessions.find_one({"user_id": user_id, "expires_at": {"$gt": datetime.now()}})
        return session["expires_at"] if session else None
    
    def end_temp_admin_session(self, user_id: int):
        result = self.admin_sessions.delete_many({"user_id": user_id})
        cache.set_admin_cache(user_id, None)
        return result.deleted_count > 0
    
    def terminate_temp_admin(self, user_id: int, terminated_by: int):
        session = self.admin_sessions.find_one({"user_id": user_id})
        if session:
            self.admin_sessions.delete_many({"user_id": user_id})
            self.temp_admins.update_one({"user_id": user_id}, {"$set": {"terminated_by": terminated_by, "terminated_at": datetime.now(), "is_terminated": True}})
            cache.set_admin_cache(user_id, None)
            return True
        return False
    
    def get_active_temp_admins(self):
        return list(self.admin_sessions.find({"expires_at": {"$gt": datetime.now()}, "is_active": True}))
    
    def get_temp_admin_stats(self):
        total_temp_admins = self.temp_admins.count_documents({})
        active_temp_sessions = self.admin_sessions.count_documents({"expires_at": {"$gt": datetime.now()}})
        pipeline = [{"$group": {"_id": None, "total_logins": {"$sum": "$login_count"}, "avg_logins": {"$avg": "$login_count"}}}]
        stats = list(self.temp_admins.aggregate(pipeline))
        return {"total_temp_admins": total_temp_admins, "active_sessions": active_temp_sessions, "total_logins": stats[0]["total_logins"] if stats else 0, "avg_logins": round(stats[0]["avg_logins"], 2) if stats else 0}
    
    def cleanup_expired(self):
        expired_sessions = self.admin_sessions.delete_many({"expires_at": {"$lt": datetime.now()}})
        expired_keys = self.login_keys.delete_many({"expires_at": {"$lt": datetime.now()}})
        return expired_sessions.deleted_count + expired_keys.deleted_count
    
    # Ban Management
    def ban_user(self, user_id: int, banned_by: int, reason: str = None):
        try:
            user = self.users.find_one({"user_id": user_id})
            self.banned_users.update_one({"user_id": user_id}, {"$set": {"banned_by": banned_by, "banned_at": datetime.now(), "reason": reason or "No reason provided", "username": user.get("username") if user else None, "first_name": user.get("first_name") if user else None}}, upsert=True)
            cache.set_banned_cache(user_id, True)
            cache.invalidate_user(user_id)
            return True
        except Exception as e:
            logger.error(f"Error banning user: {e}")
            return False
    
    def unban_user(self, user_id: int, unbanned_by: int):
        try:
            result = self.banned_users.delete_one({"user_id": user_id})
            if result.deleted_count > 0:
                cache.set_banned_cache(user_id, False)
                return True
            return False
        except Exception as e:
            logger.error(f"Error unbanning user: {e}")
            return False
    
    def get_ban_info(self, user_id: int):
        return self.banned_users.find_one({"user_id": user_id})
    
    def get_all_banned_users(self, limit: int = 100, skip: int = 0):
        return list(self.banned_users.find({}).sort("banned_at", -1).skip(skip).limit(limit))
    
    def get_banned_users_count(self):
        return self.banned_users.count_documents({})
    
    def search_banned_users(self, search_term: str):
        try:
            user_id = int(search_term)
            return list(self.banned_users.find({"user_id": user_id}))
        except:
            return list(self.banned_users.find({"$or": [{"username": {"$regex": search_term, "$options": "i"}}, {"first_name": {"$regex": search_term, "$options": "i"}}]}))
    
    # User Management
    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        existing = self.users.find_one({"user_id": user_id})
        is_new = existing is None
        self.users.update_one({"user_id": user_id}, {"$set": {"username": username, "first_name": first_name, "last_active": datetime.now()}, "$setOnInsert": {"created_at": datetime.now(), "age_verified": False, "gender": None, "welcome_sent": False}}, upsert=True)
        self.create_user_record(user_id, username, first_name)
        cache.invalidate_user(user_id)
        return is_new
    
    def update_user_age_verified(self, user_id: int, verified: bool = True):
        self.users.update_one({"user_id": user_id}, {"$set": {"age_verified": verified}})
        cache.invalidate_user(user_id)
    
    def update_user_gender(self, user_id: int, gender: str):
        self.users.update_one({"user_id": user_id}, {"$set": {"gender": gender}})
        cache.invalidate_user(user_id)
    
    def update_user_welcome_sent(self, user_id: int, sent: bool = True):
        self.users.update_one({"user_id": user_id}, {"$set": {"welcome_sent": sent}})
    
    def get_user(self, user_id: int):
        cached = cache.get_user(user_id)
        if cached:
            return cached
        user = self.users.find_one({"user_id": user_id})
        if user:
            cache.set_user(user_id, user)
        return user
    
    def get_all_users(self):
        return list(self.users.find({}, {"user_id": 1, "_id": 0}))
    
    def get_total_users(self):
        return self.users.count_documents({})
    
    def get_verified_users(self):
        return self.users.count_documents({"age_verified": True})
    
    def get_today_users(self):
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.users.count_documents({"created_at": {"$gte": today}})
    
    def get_gender_stats(self):
        male = self.users.count_documents({"gender": "male"})
        female = self.users.count_documents({"gender": "female"})
        return male, female
    
    # User Records
    def create_user_record(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        try:
            self.user_records.update_one({"user_id": user_id}, {"$set": {"username": username, "first_name": first_name, "last_name": last_name, "full_name": f"{first_name or ''} {last_name or ''}".strip(), "last_updated": datetime.now()}, "$setOnInsert": {"created_at": datetime.now(), "total_logins": 0, "total_commands": 0, "total_apk_downloads": 0, "total_demo_views": 0, "last_active": datetime.now(), "status": "active"}}, upsert=True)
            return True
        except Exception as e:
            logger.error(f"Error creating user record: {e}")
            return False
    
    def add_user_login(self, user_id: int, login_type: str = "start"):
        try:
            self.user_logins.insert_one({"user_id": user_id, "login_type": login_type, "login_time": datetime.now(), "ip": None, "user_agent": "Telegram Bot"})
            self.user_records.update_one({"user_id": user_id}, {"$inc": {"total_logins": 1, "total_commands": 1}, "$set": {"last_active": datetime.now()}})
            return True
        except Exception as e:
            logger.error(f"Error adding user login: {e}")
            return False
    
    def add_user_action(self, user_id: int, action_type: str, action_details: str = None):
        try:
            update_fields = {}
            if action_type == "apk_download":
                update_fields = {"$inc": {"total_apk_downloads": 1}}
            elif action_type == "demo_view":
                update_fields = {"$inc": {"total_demo_views": 1}}
            elif action_type == "command":
                update_fields = {"$inc": {"total_commands": 1}}
            if update_fields:
                self.user_records.update_one({"user_id": user_id}, {**update_fields, "$set": {"last_active": datetime.now()}})
            if action_details:
                self.user_actions.insert_one({"user_id": user_id, "action_type": action_type, "action_details": action_details, "timestamp": datetime.now()})
            return True
        except Exception as e:
            logger.error(f"Error adding user action: {e}")
            return False
    
    def get_user_record(self, user_id: int):
        return self.user_records.find_one({"user_id": user_id})
    
    def get_user_login_history(self, user_id: int, limit: int = 10):
        return list(self.user_logins.find({"user_id": user_id}).sort("login_time", -1).limit(limit))
    
    def get_all_user_records(self, limit: int = 100, skip: int = 0):
        return list(self.user_records.find({}).sort("last_active", -1).skip(skip).limit(limit))
    
    def get_user_records_count(self):
        return self.user_records.count_documents({})
    
    def search_users(self, search_term: str):
        try:
            user_id = int(search_term)
            return list(self.user_records.find({"user_id": user_id}))
        except:
            return list(self.user_records.find({"$or": [{"username": {"$regex": search_term, "$options": "i"}}, {"first_name": {"$regex": search_term, "$options": "i"}}, {"full_name": {"$regex": search_term, "$options": "i"}}]}).sort("last_active", -1))
    
    def get_active_users_today(self):
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self.user_records.count_documents({"last_active": {"$gte": today_start}})
    
    def get_active_users_week(self):
        week_ago = datetime.now() - timedelta(days=7)
        return self.user_records.count_documents({"last_active": {"$gte": week_ago}})
    
    def get_active_users_month(self):
        month_ago = datetime.now() - timedelta(days=30)
        return self.user_records.count_documents({"last_active": {"$gte": month_ago}})
    
    def get_user_stats_summary(self):
        total_users = self.user_records.count_documents({})
        active_today = self.get_active_users_today()
        active_week = self.get_active_users_week()
        active_month = self.get_active_users_month()
        top_users = list(self.user_records.find({}).sort("total_logins", -1).limit(5))
        return {"total": total_users, "active_today": active_today, "active_week": active_week, "active_month": active_month, "top_users": top_users}
    
    # Video Management
    def add_welcome_video(self, video_file_id: str, caption: str = None):
        return self.welcome_videos.insert_one({"video_file_id": video_file_id, "caption": caption, "created_at": datetime.now()}).inserted_id
    
    def get_all_welcome_videos(self):
        return list(self.welcome_videos.find({}))
    
    def delete_welcome_video(self, video_id):
        try:
            self.welcome_videos.delete_one({"_id": ObjectId(video_id)})
            return True
        except:
            return False
    
    def get_welcome_videos_count(self):
        return self.welcome_videos.count_documents({})
    
    def add_demo_video(self, video_file_id: str, caption: str = None):
        return self.demo_videos.insert_one({"video_file_id": video_file_id, "caption": caption, "created_at": datetime.now()}).inserted_id
    
    def get_all_demo_videos(self):
        return list(self.demo_videos.find({}))
    
    def delete_demo_video(self, video_id):
        try:
            self.demo_videos.delete_one({"_id": ObjectId(video_id)})
            return True
        except:
            return False
    
    def get_demo_videos_count(self):
        return self.demo_videos.count_documents({})
    
    # How-to Management
    def set_howto_video(self, video_file_id: str):
        self.howto_videos.delete_many({})
        self.howto_videos.insert_one({"video_file_id": video_file_id, "created_at": datetime.now()})
    
    def get_howto_video(self):
        return self.howto_videos.find_one()
    
    def delete_howto_video(self):
        self.howto_videos.delete_many({})
    
    def set_howto_text(self, text: str):
        self.howto_texts.delete_many({})
        self.howto_texts.insert_one({"text": text, "updated_at": datetime.now()})
    
    def get_howto_text(self):
        return self.howto_texts.find_one()
    
    def delete_howto_text(self):
        self.howto_texts.delete_many({})
    
    def has_howto_content(self):
        return self.howto_texts.count_documents({}) > 0 or self.howto_videos.count_documents({}) > 0
    
    # APK Management
    def add_apk_message(self, message_id: int, channel_id: int, name: str = "APK File"):
        try:
            return self.apk_messages.insert_one({"message_id": message_id, "channel_id": channel_id, "name": name, "created_at": datetime.now()}).inserted_id
        except:
            return None
    
    def get_all_apk_messages(self):
        return list(self.apk_messages.find({}))
    
    def delete_apk_message(self, message_id):
        try:
            self.apk_messages.delete_one({"_id": ObjectId(message_id)})
            return True
        except:
            return False
    
    def get_apk_messages_count(self):
        return self.apk_messages.count_documents({})
    
    # Admin Management
    def add_admin(self, user_id: int, added_by: int) -> bool:
        try:
            self.admins.insert_one({"user_id": user_id, "added_by": added_by, "added_at": datetime.now(), "is_owner": False})
            cache.set_admin_cache(user_id, True)
            return True
        except:
            return False
    
    def remove_admin(self, user_id: int) -> bool:
        if user_id == OWNER_ID:
            return False
        result = self.admins.delete_one({"user_id": user_id})
        if result.deleted_count > 0:
            cache.set_admin_cache(user_id, None)
        return result.deleted_count > 0
    
    def get_all_admins(self):
        return list(self.admins.find({}, {"user_id": 1, "is_owner": 1, "_id": 0}))

db = Database()
