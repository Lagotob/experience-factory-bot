import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, DATABASE_URL, ADMIN_IDS, GROUP_ID
from database import db

# Enable logging
logging.basicConfig(level=logging.INFO)

# Create bot and dispatcher
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Import routers
from handlers import router as handlers_router
from moderation import router as moderation_router

# Include routers
dp.include_router(handlers_router)
dp.include_router(moderation_router)


async def main():
    print("🤖 Bot is starting...")

    # Connect to database
    try:
        await db.connect()
        print("✅ Database connected!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    # Create tables
    try:
        await db.create_tables()
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return

    # Start bot polling (simpler than webhook)
    print("🚀 Starting bot polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())