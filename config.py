import logging
import os

# Bot Configuration
BOT_TOKEN = "8791838253:AAGlGP7hx_76Xvac2jTYr0kBsTVkaj0dAFQ"
OWNER_ID = 1451422178
MONGO_URI = "mongodb+srv://king:kai@cluster0.pv2q7id.mongodb.net/?appName=Cluster0"
MONGO_DB_NAME = "telegram_bot_db"
SOURCE_CHANNEL_ID = -1003960878285
APK_MESSAGE_ID = 3

# Performance settings
CPU_ALERT_THRESHOLD = 80
CHECK_INTERVAL = 120
CACHE_TTL = 300
MESSAGE_DELAY = 0.1

# Default settings
DEFAULT_ADMIN_PASSWORD = "27"
DEFAULT_TEMP_ADMIN_TIMEOUT = 24 * 60 * 60

# Questions
AGE_QUESTION = "Hey! 😍 Are you 18+"
GENDER_QUESTION = "What's your gender? 🥰🥰"

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
