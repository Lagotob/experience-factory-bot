import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config import BOT_TOKEN, DATABASE_URL, ADMIN_IDS, GROUP_ID
from database import db

# Enable logging
logging.basicConfig(level=logging.INFO)

# Create bot
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Import routers
from handlers import router as handlers_router
from moderation import router as moderation_router

# Include routers
dp.include_router(handlers_router)
dp.include_router(moderation_router)

# Webhook settings
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "") + WEBHOOK_PATH


async def on_startup():
    """When bot starts"""
    print("🤖 Bot is starting...")

    # Connect to database
    await db.connect()

    # Create tables
    await db.create_tables()

    # Set webhook
    if WEBHOOK_URL.startswith("https://"):
        await bot.set_webhook(WEBHOOK_URL)
        print(f"✅ Webhook set to: {WEBHOOK_URL}")
    else:
        print("⚠️ Running in polling mode (local development)")
        await bot.delete_webhook(drop_pending_updates=True)


async def on_shutdown():
    """When bot shuts down"""
    print("🛑 Bot is stopping...")
    await bot.delete_webhook()
    if db.pool:
        await db.pool.close()


def main():
    """Main entry point"""

    # Check if running on Render
    if os.getenv("RENDER"):
        # Production mode (webhook)
        app = web.Application()

        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        # Register startup/shutdown
        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)

        # Get port from environment
        port = int(os.getenv("PORT", 8080))

        print(f"🚀 Starting bot on port {port}")
        web.run_app(app, host="0.0.0.0", port=port)
    else:
        # Development mode (polling)
        async def polling_main():
            await on_startup()
            await dp.start_polling(bot)

        asyncio.run(polling_main())


if __name__ == "__main__":
    main()