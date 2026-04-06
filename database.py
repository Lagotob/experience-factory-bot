import asyncpg
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        print("✅ Database connected!")

    async def create_tables(self):
        """Veb-sayt (Express) bilan bir xil jadval — Telegram user_id = user_id."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    full_name VARCHAR(600) DEFAULT '',
                    password VARCHAR(600),
                    region VARCHAR(255) DEFAULT '',
                    school VARCHAR(255) DEFAULT '',
                    bio TEXT DEFAULT '',
                    avatar_data TEXT DEFAULT '',
                    xp INTEGER DEFAULT 0,
                    coins INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    completed_tasks INTEGER DEFAULT 0,
                    warnings_count INTEGER DEFAULT 0,
                    last_seen_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS quest_submissions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    quest_name VARCHAR(200),
                    proof_type VARCHAR(20),
                    proof_content TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    submitted_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    approved_at TIMESTAMPTZ,
                    admin_note TEXT
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_quests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    quest_date DATE DEFAULT CURRENT_DATE,
                    quests_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, quest_date)
                )
            """)
            print("✅ Tables OK (unified with web)")

    async def get_user(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    async def create_user(self, user_id, username, first_name, last_name=None):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, full_name)
                VALUES ($1, $2, $3, $4, COALESCE($3, ''))
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = COALESCE(EXCLUDED.last_name, users.last_name)
            """, user_id, username, first_name, last_name)

    async def update_user_stats(self, user_id, xp_delta=0, coins_delta=0):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users SET xp = xp + $2, coins = coins + $3
                WHERE user_id = $1
            """, user_id, xp_delta, coins_delta)

    async def add_warning(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET warnings_count = warnings_count + 1 WHERE user_id = $1",
                user_id
            )
            user = await conn.fetchrow(
                "SELECT warnings_count FROM users WHERE user_id = $1",
                user_id
            )
            return user["warnings_count"] if user else 0

    async def reset_warnings(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET warnings_count = 0 WHERE user_id = $1",
                user_id
            )

    async def add_quest_submission(self, user_id, quest_name, proof_type, proof_content):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                INSERT INTO quest_submissions (user_id, quest_name, proof_type, proof_content)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, user_id, quest_name, proof_type, proof_content)
            return result["id"]

    async def get_pending_quests(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT q.*, u.username, u.first_name
                FROM quest_submissions q
                JOIN users u ON q.user_id = u.user_id
                WHERE q.status = 'pending'
                ORDER BY q.submitted_at DESC
            """)

    async def approve_quest(self, submission_id, admin_note=None):
        async with self.pool.acquire() as conn:
            submission = await conn.fetchrow(
                "SELECT user_id FROM quest_submissions WHERE id = $1",
                submission_id
            )
            if submission:
                await conn.execute("""
                    UPDATE quest_submissions
                    SET status = 'approved', approved_at = CURRENT_TIMESTAMP, admin_note = $2
                    WHERE id = $1
                """, submission_id, admin_note)
                await conn.execute("""
                    UPDATE users SET
                        xp = xp + 100,
                        coins = coins + 50,
                        completed_tasks = completed_tasks + 1
                    WHERE user_id = $1
                """, submission["user_id"])
                return True
        return False

    async def reject_quest(self, submission_id, admin_note=None):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE quest_submissions SET status = 'rejected', admin_note = $2
                WHERE id = $1
            """, submission_id, admin_note)
            return True

    async def get_daily_top_users(self, limit=3):
        """Kunlik reyting o'rniga hozircha umumiy TOP (jadval to'ldirilguncha)."""
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT first_name, username, completed_tasks, xp
                FROM users
                ORDER BY xp DESC
                LIMIT $1
            """, limit)


db = Database()
