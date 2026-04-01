from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from config import ADMIN_IDS
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

router = Router()


# State for quest submission
class QuestSubmission(StatesGroup):
    waiting_for_quest_name = State()
    waiting_for_proof = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user

    # Save user to database
    await db.create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    # Get user stats
    user_data = await db.get_user(user.id)

    await message.answer(
        f"👋 <b>Xush kelibsiz, {user.first_name}!</b>\n\n"
        f"Experience Factory'ga xush kelibsiz!\n\n"
        f"📊 <b>Sizning ma'lumotlaringiz:</b>\n"
        f"⭐ XP: {user_data['xp'] if user_data else 0}\n"
        f"🪙 Tanga: {user_data['coins'] if user_data else 0}\n"
        f"📈 Daraja: {user_data['level'] if user_data else 1}\n\n"
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
    user = message.from_user

    # Get user from database
    user_data = await db.get_user(user.id)

    if not user_data:
        await message.answer("❌ Siz hali ro'yxatdan o'tmagansiz. Iltimos /start bosing")
        return

    # Calculate XP needed for next level
    xp_needed = user_data['level'] * 100 - user_data['xp']

    await message.answer(
        f"📊 <b>Sizning profilingiz</b>\n\n"
        f"👤 Ism: {user_data['first_name']}\n"
        f"🆔 Username: @{user_data['username'] or 'mavjud emas'}\n"
        f"⭐ XP: {user_data['xp']}\n"
        f"🪙 Tanga: {user_data['coins']}\n"
        f"📈 Daraja: {user_data['level']}\n"
        f"✅ Bajarilgan topshiriqlar: {user_data['total_quests']}\n"
        f"⚠️ Ogohlantirishlar: {user_data['warnings']}\n\n"
        f"🎯 Keyingi daraja uchun: {xp_needed} XP kerak",
    )


@router.message(Command("submit_quest"))
async def cmd_submit_quest(message: types.Message, state: FSMContext):
    await message.answer("📝 <b>Topshiriq nomini yozing:</b>\n\nMisol: 'Kunlik vazifa - 1-dars'")
    await state.set_state(QuestSubmission.waiting_for_quest_name)


@router.message(QuestSubmission.waiting_for_quest_name)
async def process_quest_name(message: types.Message, state: FSMContext):
    quest_name = message.text
    await state.update_data(quest_name=quest_name)

    await message.answer(
        "📎 <b>Topshiriq isbotini yuboring:</b>\n\n"
        "Rasm, video, fayl yoki matn ko'rinishida yuborishingiz mumkin."
    )
    await state.set_state(QuestSubmission.waiting_for_proof)


@router.message(QuestSubmission.waiting_for_proof)
async def process_proof(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    quest_name = user_data.get('quest_name')

    # Determine proof type and content
    if message.photo:
        proof_type = "photo"
        proof_content = message.photo[-1].file_id
    elif message.video:
        proof_type = "video"
        proof_content = message.video.file_id
    elif message.document:
        proof_type = "file"
        proof_content = message.document.file_id
    elif message.text:
        proof_type = "text"
        proof_content = message.text
    else:
        await message.answer("❌ Iltimos, rasm, video, fayl yoki matn yuboring!")
        return

    # Save to database
    submission_id = await db.add_quest_submission(
        user_id=message.from_user.id,
        quest_name=quest_name,
        proof_type=proof_type,
        proof_content=proof_content
    )

    await message.answer(
        f"✅ <b>Topshiriq muvaffaqiyatli yuborildi!</b>\n\n"
        f"📌 Topshiriq: {quest_name}\n"
        f"🆔 ID: {submission_id}\n\n"
        f"Adminga yuborildi. Tez orada tekshiriladi va tasdiqlanadi."
    )

    await state.clear()


# Admin Commands

@router.message(Command("pending"))
async def cmd_pending(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Bu komanda faqat adminlar uchun!")
        return

    pending_quests = await db.get_pending_quests()

    if not pending_quests:
        await message.answer("📭 Hozircha kutilayotgan topshiriqlar yo'q.")
        return

    for quest in pending_quests[:5]:
        # Create inline buttons
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{quest['id']}"),
                    InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{quest['id']}")
                ]
            ]
        )

        # Determine proof preview
        proof_preview = ""
        if quest['proof_type'] == "photo":
            proof_preview = "📸 Rasm (telegramda oching)"
        elif quest['proof_type'] == "video":
            proof_preview = "🎥 Video (telegramda oching)"
        elif quest['proof_type'] == "file":
            proof_preview = "📎 Fayl (telegramda oching)"
        else:
            proof_preview = f"📝 Matn: {quest['proof_content'][:100]}..."

        await message.answer(
            f"📋 <b>Topshiriq #{quest['id']}</b>\n\n"
            f"👤 Foydalanuvchi: {quest['first_name']} (@{quest['username'] or 'no username'})\n"
            f"📌 Topshiriq: {quest['quest_name']}\n"
            f"📎 Isbot turi: {quest['proof_type']}\n"
            f"📄 Isbot: {proof_preview}\n"
            f"🕐 Vaqt: {quest['submitted_at']}\n\n"
            f"👇 Quyidagi tugmalar orqali tasdiqlang yoki rad eting:",
            reply_markup=keyboard
        )


@router.message(Command("reward"))
async def cmd_reward(message: types.Message):
    """Admin command to reward users"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Bu komanda faqat adminlar uchun!")
        return

    # Parse command: /reward @username 100
    parts = message.text.split()

    if len(parts) < 3:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Ishlatish: /reward @username XP\n"
            "Misol: /reward @john 50 (50 XP va 25 coins beradi)"
        )
        return

    # Get username (remove @ if present)
    username = parts[1].replace("@", "")

    try:
        reward_xp = int(parts[2])
        reward_coins = reward_xp // 2
    except ValueError:
        await message.answer("❌ XP soni raqam bo'lishi kerak!")
        return

    # Find user in database by username
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT user_id, first_name FROM users WHERE username = $1",
            username
        )

        if not user:
            await message.answer(f"❌ @{username} topilmadi!")
            return

        # Update user stats
        await db.update_user_stats(
            user_id=user['user_id'],
            xp_delta=reward_xp,
            coins_delta=reward_coins
        )

        await message.answer(
            f"✅ <b>@{username} mukofotlandi!</b>\n\n"
            f"⭐ +{reward_xp} XP\n"
            f"🪙 +{reward_coins} Tanga\n\n"
            f"👤 Foydalanuvchi: {user['first_name']}"
        )

        # Try to notify user
        try:
            await message.bot.send_message(
                chat_id=user['user_id'],
                text=f"🎉 <b>Siz mukofotlandingiz!</b>\n\n"
                     f"⭐ +{reward_xp} XP\n"
                     f"🪙 +{reward_coins} Tanga\n\n"
                     f"Admin: @{message.from_user.username or message.from_user.first_name}\n"
                     f"Sabab: Yaxshi faoliyat uchun!\n\n"
                     f"Statistikangizni ko'rish: /my_stats"
            )
        except:
            pass


@router.message(Command("warn"))
async def cmd_warn(message: types.Message):
    """Admin command to warn users"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Bu komanda faqat adminlar uchun!")
        return

    parts = message.text.split()

    if len(parts) < 2:
        await message.answer("Ishlatish: /warn @username [sabab]")
        return

    username = parts[1].replace("@", "")
    reason = " ".join(parts[2:]) if len(parts) > 2 else "Sabab ko'rsatilmagan"

    # Find user
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT user_id, first_name, warnings FROM users WHERE username = $1",
            username
        )

        if not user:
            await message.answer(f"❌ @{username} topilmadi!")
            return

        # Add warning
        new_warning_count = await db.add_warning(user['user_id'])

        await message.answer(
            f"⚠️ <b>@{username} ogohlantirish oldi!</b>\n\n"
            f"Sabab: {reason}\n"
            f"Ogohlantirishlar: {new_warning_count}/3\n\n"
            f"3-ogohlantirishdan keyin guruhdan chiqarib yuboriladi."
        )

        # Notify user
        try:
            await message.bot.send_message(
                chat_id=user['user_id'],
                text=f"⚠️ <b>Siz ogohlantirish oldingiz!</b>\n\n"
                     f"Sabab: {reason}\n"
                     f"Ogohlantirishlar: {new_warning_count}/3\n\n"
                     f"<i>Guruh qoidalariga rioya qiling!</i>"
            )
        except:
            pass


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    """Show top users leaderboard"""

    # Parse command: /leaderboard or /leaderboard xp|coins|quests
    parts = message.text.split()
    sort_by = "xp"  # default

    if len(parts) > 1:
        if parts[1].lower() in ["coins", "coin", "tanga"]:
            sort_by = "coins"
        elif parts[1].lower() in ["quests", "quest", "topshiriq"]:
            sort_by = "quests"

    # Get leaderboard
    top_users = await db.get_leaderboard(limit=10, sort_by=sort_by)

    if not top_users:
        await message.answer("📊 Hozircha leaderboard bo'sh. Birinchi bo'ling!")
        return

    # Create leaderboard text
    if sort_by == "xp":
        title = "⭐ XP BO'YICHA TOP 10 ⭐"
        value_field = "xp"
        value_name = "XP"
    elif sort_by == "coins":
        title = "🪙 TANGA BO'YICHA TOP 10 🪙"
        value_field = "coins"
        value_name = "Tanga"
    else:
        title = "✅ TOPSHIRIQLAR BO'YICHA TOP 10 ✅"
        value_field = "total_quests"
        value_name = "Topshiriq"

    leaderboard_text = f"🏆 <b>{title}</b>\n\n"

    for i, user in enumerate(top_users, 1):
        medal = ""
        if i == 1:
            medal = "🥇 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        else:
            medal = f"{i}. "

        name = user['first_name'][:20]  # Limit name length
        if user['username']:
            name_display = f"@{user['username']}"
        else:
            name_display = name

        value = user[value_field]

        leaderboard_text += f"{medal}{name_display} — <b>{value}</b> {value_name}\n"

    # Get user's own rank
    user_rank = await db.get_user_rank(message.from_user.id, sort_by)
    user_data = await db.get_user(message.from_user.id)

    if user_data:
        leaderboard_text += f"\n📊 <b>Sizning joyingiz:</b> #{user_rank} ( {user_data[value_field]} {value_name} )"

    await message.answer(leaderboard_text)


@router.message(Command("top"))
async def cmd_top(message: types.Message):
    """Show daily top users"""

    daily_top = await db.get_daily_top_users(limit=5)

    if not daily_top:
        await message.answer("📊 Bugun hali hech kim topshiriq bajarmagan. Birinchi bo'ling!")
        return

    top_text = "🌟 <b>BUGUNGI ENG FAOL FOYDALANUVCHILAR</b> 🌟\n\n"

    for i, user in enumerate(daily_top, 1):
        medal = ""
        if i == 1:
            medal = "🏆 "
        elif i == 2:
            medal = "🥈 "
        elif i == 3:
            medal = "🥉 "
        else:
            medal = f"{i}. "

        name = user['first_name']
        if user['username']:
            name_display = f"@{user['username']}"
        else:
            name_display = name

        top_text += f"{medal}{name_display} — <b>{user['quests_count']}</b> topshiriq\n"

    await message.answer(top_text)


@router.callback_query(lambda c: c.data.startswith('approve_'))
async def approve_quest_callback(callback_query: CallbackQuery):
    """Handle approve button click"""

    # Check if user is admin
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Bu faqat adminlar uchun!", show_alert=True)
        return

    # Get submission ID from callback data
    submission_id = int(callback_query.data.split('_')[1])

    # Approve quest
    success = await db.approve_quest(submission_id, admin_note=f"Approved by {callback_query.from_user.first_name}")

    if success:
        # Get submission details to notify user
        async with db.pool.acquire() as conn:
            submission = await conn.fetchrow(
                "SELECT user_id, quest_name FROM quest_submissions WHERE id = $1",
                submission_id
            )

            if submission:
                # Notify user
                try:
                    await callback_query.bot.send_message(
                        chat_id=submission['user_id'],
                        text=f"✅ <b>Topshiriq tasdiqlandi!</b>\n\n"
                             f"📌 Topshiriq: {submission['quest_name']}\n"
                             f"⭐ +100 XP\n"
                             f"🪙 +50 Tanga\n\n"
                             f"Admin: @{callback_query.from_user.username or callback_query.from_user.first_name}\n\n"
                             f"Statistikangizni ko'rish: /my_stats"
                    )
                except:
                    pass

        # Update the message
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n✅ <b>TASDIQLANDI!</b>",
            parse_mode="HTML"
        )
        await callback_query.answer("✅ Topshiriq tasdiqlandi!")
    else:
        await callback_query.answer("❌ Xatolik yuz berdi!", show_alert=True)


@router.callback_query(lambda c: c.data.startswith('reject_'))
async def reject_quest_callback(callback_query: CallbackQuery):
    """Handle reject button click"""

    # Check if user is admin
    if callback_query.from_user.id not in ADMIN_IDS:
        await callback_query.answer("❌ Bu faqat adminlar uchun!", show_alert=True)
        return

    # Get submission ID from callback data
    submission_id = int(callback_query.data.split('_')[1])

    # Ask for reason
    await callback_query.message.answer(
        f"❌ Rad etish sababini yozing (ID: {submission_id}):\n\n"
        f"Misol: 'Noto'g'ri isbot yuborilgan'",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_reject_{submission_id}")
            ]]
        )
    )

    # Store submission ID for next message
    import json
    # We'll handle this in next message
    await callback_query.answer()


# You'll need to add a state for rejection reason
from aiogram.fsm.state import State, StatesGroup


class RejectReason(StatesGroup):
    waiting_for_reason = State()


@router.callback_query(lambda c: c.data.startswith('cancel_reject_'))
async def cancel_reject(callback_query: CallbackQuery, state: FSMContext):
    """Cancel rejection"""
    await state.clear()
    await callback_query.message.delete()
    await callback_query.answer("❌ Rad etish bekor qilindi!", show_alert=True)


@router.message(RejectReason.waiting_for_reason)
async def process_reject_reason(message: types.Message, state: FSMContext):
    """Process rejection reason"""

    # Check if user is admin
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Bu faqat adminlar uchun!")
        await state.clear()
        return

    data = await state.get_data()
    submission_id = data.get('submission_id')
    reason = message.text

    # Reject quest
    success = await db.reject_quest(submission_id, admin_note=reason)

    if success:
        # Get submission details
        async with db.pool.acquire() as conn:
            submission = await conn.fetchrow(
                "SELECT user_id, quest_name FROM quest_submissions WHERE id = $1",
                submission_id
            )

            if submission:
                # Notify user
                try:
                    await message.bot.send_message(
                        chat_id=submission['user_id'],
                        text=f"❌ <b>Topshiriq rad etildi!</b>\n\n"
                             f"📌 Topshiriq: {submission['quest_name']}\n"
                             f"📝 Sabab: {reason}\n\n"
                             f"Admin: @{message.from_user.username or message.from_user.first_name}\n\n"
                             f"<i>Topshiriqni qayta yuborishingiz mumkin: /submit_quest</i>"
                    )
                except:
                    pass

        await message.answer(f"✅ Topshiriq #{submission_id} rad etildi!\n\nSabab: {reason}")
    else:
        await message.answer("❌ Xatolik yuz berdi!")

    await state.clear()


@router.message(Command("groupid"))
async def cmd_groupid(message: types.Message):
    """Get group ID (admin only)"""

    # Check if command is used in a group
    if message.chat.type in ["group", "supergroup"]:
        # Check if user is admin of the group
        try:
            chat_admins = await message.bot.get_chat_administrators(message.chat.id)
            admin_ids = [admin.user.id for admin in chat_admins]

            if message.from_user.id in admin_ids:
                await message.answer(
                    f"📊 <b>Guruh ma'lumotlari:</b>\n\n"
                    f"📝 Guruh nomi: {message.chat.title}\n"
                    f"🆔 Guruh ID: <code>{message.chat.id}</code>\n\n"
                    f"<i>Bu ID ni .env faylida GROUP_ID ga qo'shing:</i>\n"
                    f"<code>GROUP_ID={message.chat.id}</code>"
                )
            else:
                await message.answer("❌ Bu komanda faqat guruh adminlari uchun!")
        except Exception as e:
            await message.answer(f"❌ Xatolik: Bot admin huquqiga ega emas!")
    else:
        await message.answer(
            "❌ Bu komanda faqat guruhlarda ishlaydi!\n\n"
            "Botni guruhga qo'shing va shu yerdan foydalaning."
        )