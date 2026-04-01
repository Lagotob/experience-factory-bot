import re
import time
import asyncio
from aiogram import Router, types, Bot
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER
from aiogram.types import ChatMemberUpdated
from database import db

router = Router()

# Track which groups have been welcomed
_welcomed_groups = set()

# Bad words list (add your own words)
BAD_WORDS = [
    # Add your bad words here
    "fuck", "shit", "asshole",
]

# Spam detection
USER_MESSAGES = {}


def contains_bad_words(text: str) -> bool:
    """Check if text contains any bad words"""
    if not text:
        return False

    text_lower = text.lower()
    for word in BAD_WORDS:
        if word.lower() in text_lower:
            return True
    return False


def is_spam(user_id: int) -> bool:
    """Check if user is spamming"""
    current_time = time.time()

    if user_id not in USER_MESSAGES:
        USER_MESSAGES[user_id] = []

    USER_MESSAGES[user_id] = [t for t in USER_MESSAGES[user_id] if current_time - t < 10]

    if len(USER_MESSAGES[user_id]) >= 5:
        return True

    USER_MESSAGES[user_id].append(current_time)
    return False


async def apply_punishment(message: types.Message, warning_count: int, bot: Bot):
    """Apply punishment based on warning count"""

    if warning_count == 2:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            permissions=types.ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=int(time.time()) + 600
        )

        mute_msg = await message.answer(
            f"🔇 <b>@{message.from_user.username or message.from_user.first_name} 2-ogohlantirish oldi!</b>\n"
            f"10 daqiqaga ovoz o'chirildi.\n\n"
            f"<i>3-ogohlantirishdan keyin guruhdan chiqarib yuborilasiz!</i>"
        )

        await asyncio.sleep(10)
        try:
            await mute_msg.delete()
        except:
            pass

    elif warning_count >= 3:
        await bot.ban_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id
        )
        await bot.unban_chat_member(
            chat_id=message.chat.id,
            user_id=message.from_user.id
        )

        kick_msg = await message.answer(
            f"🚫 <b>@{message.from_user.username or message.from_user.first_name} guruhdan chiqarib yuborildi!</b>\n"
            f"Sabab: 3 marta ogohlantirish olindi."
        )

        await asyncio.sleep(10)
        try:
            await kick_msg.delete()
        except:
            pass

        await db.reset_warnings(message.from_user.id)


@router.my_chat_member()
async def bot_status_change(event: ChatMemberUpdated):
    """Handle bot status changes in groups"""

    # Only handle when bot itself is updated
    if event.new_chat_member.user.id != (await event.bot.get_me()).id:
        return

    group_id = event.chat.id

    # Check if bot is now a member
    if event.new_chat_member.status in ["member", "administrator"]:
        # Check if we already sent welcome for this group
        if group_id in _welcomed_groups:
            return

        # Check if bot has admin rights
        if event.new_chat_member.status == "administrator":
            # Bot has admin rights, mark as welcomed
            _welcomed_groups.add(group_id)
            await event.answer(
                "✅ <b>Bot muvaffaqiyatli sozlandi!</b>\n\n"
                "Guruh boshqaruvi faollashtirildi.\n"
                "Endi bot spam va yomon so'zlarni avtomatik o'chiradi.\n\n"
                "Komandalar:\n"
                "/help - Yordam menyusi"
            )
        else:
            # Bot is member but not admin
            _welcomed_groups.add(group_id)
            await event.answer(
                "🤖 <b>Bot guruhga qo'shildi!</b>\n\n"
                "⚠️ <b>Admin huquqlari kerak!</b>\n\n"
                "Iltimos, botga quyidagi admin huquqlarini bering:\n"
                "✅ <b>Delete messages</b> - spamni o'chirish uchun\n"
                "✅ <b>Ban users</b> - qoidabuzarlarni chiqarish uchun\n"
                "✅ <b>Restrict users</b> - ovozni o'chirish uchun\n\n"
                "Admin huquqlari berilgandan so'ng bot avtomatik ishlaydi.",
                parse_mode="HTML"
            )

    # Reset welcomed status if bot is removed from group
    elif event.new_chat_member.status == "left":
        if group_id in _welcomed_groups:
            _welcomed_groups.remove(group_id)


@router.message()
async def welcome_new_members(message: types.Message, bot: Bot):
    """Welcome new members to group"""

    if message.chat.type not in ["group", "supergroup"]:
        return

    if message.new_chat_members:
        for member in message.new_chat_members:
            if member.is_bot:
                continue

            await message.answer(
                f"🎉 <b>Xush kelibsiz, {member.first_name}!</b> 🎉\n\n"
                f"Experience Factory'da ishlashga tayyormisiz?\n\n"
                f"🌐 Saytimiz: <a href='https://your-website.com'>experiencefactory.uz</a>\n\n"
                f"📊 Statistikangizni ko'rish uchun /start va /my_stats bosing\n"
                f"✅ Topshiriqlarni topshirish uchun /submit_quest",
                disable_web_page_preview=True
            )


@router.message()
async def moderate_messages(message: types.Message, bot: Bot):
    """Moderate all messages in groups"""

    if message.chat.type not in ["group", "supergroup"]:
        return

    if message.from_user.is_bot:
        return

    # Check if bot is admin
    try:
        chat_member = await bot.get_chat_member(message.chat.id, (await bot.get_me()).id)
        if chat_member.status not in ["administrator"]:
            return  # Bot is not admin, can't moderate
    except:
        return

    # Get chat admins
    try:
        chat_admins = await bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
    except:
        admin_ids = []

    if message.from_user.id in admin_ids:
        return

    # Check for spam
    if is_spam(message.from_user.id):
        await message.delete()
        warning_count = await db.add_warning(message.from_user.id)
        await apply_punishment(message, warning_count, bot)
        return

    # Check for bad words
    if message.text and contains_bad_words(message.text):
        await message.delete()
        warning_count = await db.add_warning(message.from_user.id)

        warn_msg = await message.answer(
            f"⚠️ <b>Ogohlantirish!</b> @{message.from_user.username or message.from_user.first_name}\n"
            f"Yomon so'zlar ishlatish taqiqlanadi!\n"
            f"Ogohlantirishlar: {warning_count}/3"
        )

        await asyncio.sleep(5)
        try:
            await warn_msg.delete()
        except:
            pass

        await apply_punishment(message, warning_count, bot)
        return


@router.my_chat_member()
async def bot_status_change(event: ChatMemberUpdated):
    # ... existing code ...

    # Add this line to print group ID to console
    print(f"📊 Bot added to group: {event.chat.id} - {event.chat.title}")

    # ... rest of the code