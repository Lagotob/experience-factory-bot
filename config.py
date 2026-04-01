import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Get admin IDs
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

# Get group ID
GROUP_ID_STR = os.getenv("GROUP_ID", "")
GROUP_ID = int(GROUP_ID_STR) if GROUP_ID_STR else None

# Check variables
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in .env file")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL not found in .env file")