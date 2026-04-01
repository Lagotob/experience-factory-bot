import asyncio
import datetime
from aiogram import Bot
from database import db


async def send_daily_report(bot: Bot, group_id: int):
    """Send daily top 3 report to group"""

    # Wait until 9:00 AM
    while True:
        now = datetime.datetime.now()
        target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

        if now >= target_time:
            target_time += datetime.timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Get daily top users
        daily_top = await db.get_daily_top_users(limit=3)

        if daily_top:
            report_text = "📊 <b>KUNNING ENG FAOL ISHCHILARI</b> 📊\n\n"

            for i, user in enumerate(daily_top, 1):
                medal = ""
                if i == 1:
                    medal = "🏆 1-o'rin"
                elif i == 2:
                    medal = "🥈 2-o'rin"
                elif i == 3:
                    medal = "🥉 3-o'rin"

                name = user['first_name']
                if user['username']:
                    name_display = f"@{user['username']}"
                else:
                    name_display = name

                report_text += f"{medal}: {name_display}\n"
                report_text += f"   ✅ {user['quests_count']} topshiriq bajarildi\n\n"

            report_text += "\n💪 Yana ham ko'proq topshiriqlar bajarib, liderlar qatoriga chiqing!"

            try:
                await bot.send_message(group_id, report_text)
            except Exception as e:
                print(f"Failed to send daily report: {e}")

        # Wait 24 hours before next check
        await asyncio.sleep(86400)


async def start_scheduler(bot: Bot, group_id: int):
    """Start the daily report scheduler"""
    asyncio.create_task(send_daily_report(bot, group_id))