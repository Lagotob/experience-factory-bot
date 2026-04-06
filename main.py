import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN, GROUP_ID
from database import db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

from handlers import router as handlers_router
from moderation import router as moderation_router
from scheduler import start_scheduler

dp.include_router(handlers_router)
dp.include_router(moderation_router)

async def main():
    print("🤖 Bot starting...")
    await db.connect()
    await db.create_tables()
    await bot.delete_webhook(drop_pending_updates=True)
    if GROUP_ID:
        start_scheduler(bot, GROUP_ID)
        print(f"📅 Kunlik hisobot: group_id={GROUP_ID}")
    print("✅ Bot running!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())