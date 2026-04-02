import asyncio
from aiogram import Router, types, Bot
from database import db

router = Router()

BAD_WORDS = ["fuck", "shit", "asshole", "bitch", "damn", "jinni", "ahmoq", "tentak", "eshak"]


def contains_bad_words(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word.lower() in text_lower:
            return True
    return False


@router.message()
async def moderate_messages(message: types.Message, bot: Bot):
    # Only in groups
    if message.chat.type not in ["group", "supergroup"]:
        return

    # Skip bots
    if message.from_user.is_bot:
        return

    # Check for bad words
    if message.text and contains_bad_words(message.text):
        try:
            await message.delete()
            msg = await message.answer(
                f"⚠️ @{message.from_user.username or message.from_user.first_name} Yomon so'z ishlatish taqiqlanadi!")
            await asyncio.sleep(3)
            await msg.delete()
            print(f"Deleted bad word from {message.from_user.username}")
        except Exception as e:
            print(f"Error: {e}")


@router.message()
async def welcome_new_members(message: types.Message):
    if message.chat.type not in ["group", "supergroup"]:
        return

    if message.new_chat_members:
        for member in message.new_chat_members:
            if not member.is_bot:
                await message.answer(f"🎉 <b>Xush kelibsiz, {member.first_name}!</b>\n/start - boshlang",
                                     parse_mode="HTML")