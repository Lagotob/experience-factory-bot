import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN
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
    print("🤖 Experience Factory Bot is starting...")

    # Connect to database
    await db.connect()

    # Create tables
    await db.create_tables()

    # Start bot
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Bot is running!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())