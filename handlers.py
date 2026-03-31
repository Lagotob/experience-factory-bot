from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await message.answer(
        f"👋 <b>Xush kelibsiz, {user.first_name}!</b>\n\n"
        f"Experience Factory'ga xush kelibsiz!\n"
        f"Sizning profilingiz yaratilmoqda...\n\n"
        f"Komandalar:\n"
        f"/my_stats - Profilingizni ko'rish\n"
        f"/submit_quest - Topshiriq topshirish\n"
        f"/help - Yordam"
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 <b>Yordam:</b>\n\n"
        "/start - Botni ishga tushirish\n"
        "/my_stats - Statistikangizni ko'rish\n"
        "/submit_quest - Topshiriq topshirish\n\n"
        "❓ Savollar bo'lsa, @admin ga yozing"
    )

@router.message(Command("my_stats"))
async def cmd_stats(message: types.Message):
    # Temporary message – we'll connect database next
    await message.answer(
        "📊 <b>Sizning profilingiz</b>\n\n"
        f"👤 Ism: {message.from_user.first_name}\n"
        "⭐ XP: 0\n"
        "🪙 Tanga: 0\n"
        "📈 Daraja: 1\n\n"
        "💡 <i>Ma'lumotlar bazaga ulanmoqda...</i>"
    )