import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import BOT_TOKEN

# Enable logging
logging.basicConfig(level=logging.INFO)

# Create bot with new syntax
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Import handlers after creating bot (to avoid circular imports)
from handlers import router
dp.include_router(router)

async def main():
    print("🤖 Bot is starting...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
    print("✅ Bot is running!")

if __name__ == "__main__":
    asyncio.run(main())