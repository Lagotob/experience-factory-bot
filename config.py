import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]

_group = os.getenv("GROUP_ID", "").strip()
GROUP_ID = int(_group) if _group else None

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL not found")