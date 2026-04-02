from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import db
from config import ADMIN_IDS

router = Router()


class QuestSubmission(StatesGroup):
    waiting_for_quest_name = State()
    waiting_for_proof = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    await db.create_user(user.id, user.username, user.first_name, user.last_name)
    user_data = await db.get_user(user.id)

    await message.answer(
        f"👋 <b>Xush kelibsiz, {user.first_name}!</b>\n\n"
        f"⭐ XP: {user_data['xp'] if user_data else 0}\n"
        f"🪙 Tanga: {user_data['coins'] if user_data else 0}\n"
        f"📈 Daraja: {user_data['level'] if user_data else 1}\n\n"
        f"/my_stats - Profil\n"
        f"/submit_quest - Topshiriq\n"
        f"/help - Yordam"
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 <b>Komandalar:</b>\n\n"
        "/start - Boshlash\n"
        "/my_stats - Profil\n"
        "/submit_quest - Topshiriq topshirish\n"
        "/leaderboard - Reyting\n"
        "/help - Yordam"
    )


@router.message(Command("my_stats"))
async def cmd_stats(message: types.Message):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        await message.answer("❌ /start bosing")
        return

    await message.answer(
        f"📊 <b>Profil</b>\n\n"
        f"👤 {user_data['first_name']}\n"
        f"⭐ XP: {user_data['xp']}\n"
        f"🪙 Tanga: {user_data['coins']}\n"
        f"📈 Daraja: {user_data['level']}\n"
        f"✅ Topshiriqlar: {user_data['total_quests']}\n"
        f"⚠️ Ogohlantirish: {user_data['warnings']}/3"
    )


@router.message(Command("submit_quest"))
async def cmd_submit_quest(message: types.Message, state: FSMContext):
    await message.answer("📝 Topshiriq nomini yozing:")
    await state.set_state(QuestSubmission.waiting_for_quest_name)


@router.message(QuestSubmission.waiting_for_quest_name)
async def process_quest_name(message: types.Message, state: FSMContext):
    await state.update_data(quest_name=message.text)
    await message.answer("📎 Isbot yuboring (rasm, video, fayl yoki matn):")
    await state.set_state(QuestSubmission.waiting_for_proof)


@router.message(QuestSubmission.waiting_for_proof)
async def process_proof(message: types.Message, state: FSMContext):
    data = await state.get_data()
    quest_name = data.get('quest_name')

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
        await message.answer("❌ Rasm, video, fayl yoki matn yuboring!")
        return

    submission_id = await db.add_quest_submission(message.from_user.id, quest_name, proof_type, proof_content)
    await message.answer(f"✅ Topshiriq yuborildi! ID: #{submission_id}\nAdminga yuborildi.")
    await state.clear()


@router.message(Command("pending"))
async def cmd_pending(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Admin uchun!")
        return

    pending = await db.get_pending_quests()
    if not pending:
        await message.answer("📭 Hech narsa yo'q")
        return

    for q in pending[:3]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{q['id']}"),
             InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{q['id']}")]
        ])
        await message.answer(f"📋 #{q['id']}\n👤 @{q['username']}\n📌 {q['quest_name']}", reply_markup=keyboard)


@router.callback_query(lambda c: c.data.startswith('approve_'))
async def approve_quest(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Admin emas!", show_alert=True)
        return

    submission_id = int(callback.data.split('_')[1])
    await db.approve_quest(submission_id, f"Approved by {callback.from_user.first_name}")
    await callback.message.edit_text(f"✅ #{submission_id} tasdiqlandi!")
    await callback.answer("✅ Tasdiqlandi!")


@router.callback_query(lambda c: c.data.startswith('reject_'))
async def reject_quest(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Admin emas!", show_alert=True)
        return

    submission_id = int(callback.data.split('_')[1])
    await db.reject_quest(submission_id, f"Rejected by {callback.from_user.first_name}")
    await callback.message.edit_text(f"❌ #{submission_id} rad etildi!")
    await callback.answer("❌ Rad etildi!")


@router.message(Command("leaderboard"))
async def cmd_leaderboard(message: types.Message):
    async with db.pool.acquire() as conn:
        users = await conn.fetch("SELECT username, first_name, xp FROM users ORDER BY xp DESC LIMIT 10")

    if not users:
        await message.answer("📊 Hozircha ma'lumot yo'q")
        return

    text = "🏆 <b>TOP 10 XP</b>\n\n"
    for i, u in enumerate(users, 1):
        name = u['username'] or u['first_name']
        text += f"{i}. @{name} — {u['xp']} XP\n"

    await message.answer(text)


@router.message(Command("reward"))
async def cmd_reward(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Admin uchun!")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("❌ /reward @username XP")
        return

    username = parts[1].replace("@", "")
    try:
        xp = int(parts[2])
    except:
        await message.answer("❌ XP son bo'lishi kerak!")
        return

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id, first_name FROM users WHERE username = $1", username)
        if not user:
            await message.answer(f"❌ @{username} topilmadi!")
            return

        await db.update_user_stats(user['user_id'], xp, xp // 2)
        await message.answer(f"✅ @{username} +{xp} XP, +{xp // 2} tanga!")