import asyncpg
from config import DATABASE_URL


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Create connection pool to database"""
        self.pool = await asyncpg.create_pool(DATABASE_URL)
        print("✅ Database connected!")

    async def create_tables(self):
        """Create tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Users table
            await conn.execute("""
                               CREATE TABLE IF NOT EXISTS users
                               (
                                   user_id
                                   BIGINT
                                   PRIMARY
                                   KEY,
                                   username
                                   VARCHAR
                               (
                                   100
                               ),
                                   first_name VARCHAR
                               (
                                   100
                               ),
                                   last_name VARCHAR
                               (
                                   100
                               ),
                                   xp INTEGER DEFAULT 0,
                                   coins INTEGER DEFAULT 0,
                                   level INTEGER DEFAULT 1,
                                   total_quests INTEGER DEFAULT 0,
                                   warnings INTEGER DEFAULT 0,
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                                   )
                               """)

            # Quest submissions table
            await conn.execute("""
                               CREATE TABLE IF NOT EXISTS quest_submissions
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   user_id
                                   BIGINT
                                   REFERENCES
                                   users
                               (
                                   user_id
                               ),
                                   quest_name VARCHAR
                               (
                                   200
                               ),
                                   proof_type VARCHAR
                               (
                                   20
                               ),
                                   proof_content TEXT,
                                   status VARCHAR
                               (
                                   20
                               ) DEFAULT 'pending',
                                   submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   approved_at TIMESTAMP,
                                   admin_note TEXT
                                   )
                               """)

            # Daily quest counts for leaderboard
            await conn.execute("""
                               CREATE TABLE IF NOT EXISTS daily_quests
                               (
                                   id
                                   SERIAL
                                   PRIMARY
                                   KEY,
                                   user_id
                                   BIGINT
                                   REFERENCES
                                   users
                               (
                                   user_id
                               ),
                                   quest_date DATE DEFAULT CURRENT_DATE,
                                   quests_count INTEGER DEFAULT 0,
                                   UNIQUE
                               (
                                   user_id,
                                   quest_date
                               )
                                   )
                               """)

            print("✅ Tables created successfully!")

    async def get_user(self, user_id):
        """Get user data from database"""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
            return user

    async def create_user(self, user_id, username, first_name, last_name=None):
        """Create new user if not exists"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               INSERT INTO users (user_id, username, first_name, last_name)
                               VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO NOTHING
                               """, user_id, username, first_name, last_name)

    async def update_user_stats(self, user_id, xp_delta=0, coins_delta=0):
        """Update user XP and coins"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               UPDATE users
                               SET xp    = xp + $2,
                                   coins = coins + $3
                               WHERE user_id = $1
                               """, user_id, xp_delta, coins_delta)

    async def add_warning(self, user_id):
        """Add warning to user"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               UPDATE users
                               SET warnings = warnings + 1
                               WHERE user_id = $1
                               """, user_id)

            # Get current warnings count
            user = await conn.fetchrow(
                "SELECT warnings FROM users WHERE user_id = $1",
                user_id
            )
            return user['warnings'] if user else 0

    async def reset_warnings(self, user_id):
        """Reset user warnings"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               UPDATE users
                               SET warnings = 0
                               WHERE user_id = $1
                               """, user_id)

    async def add_quest_submission(self, user_id, quest_name, proof_type, proof_content):
        """Add quest submission to database"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow("""
                                         INSERT INTO quest_submissions (user_id, quest_name, proof_type, proof_content)
                                         VALUES ($1, $2, $3, $4) RETURNING id
                                         """, user_id, quest_name, proof_type, proof_content)
            return result['id']

    async def get_pending_quests(self):
        """Get all pending quest submissions"""
        async with self.pool.acquire() as conn:
            quests = await conn.fetch("""
                                      SELECT q.*, u.username, u.first_name
                                      FROM quest_submissions q
                                               JOIN users u ON q.user_id = u.user_id
                                      WHERE q.status = 'pending'
                                      ORDER BY q.submitted_at DESC
                                      """)
            return quests

    async def approve_quest(self, submission_id, admin_note=None):
        """Approve quest and give rewards"""
        async with self.pool.acquire() as conn:
            # Get submission details
            submission = await conn.fetchrow(
                "SELECT user_id FROM quest_submissions WHERE id = $1",
                submission_id
            )

            if submission:
                # Update submission status
                await conn.execute("""
                                   UPDATE quest_submissions
                                   SET status      = 'approved',
                                       approved_at = CURRENT_TIMESTAMP,
                                       admin_note  = $2
                                   WHERE id = $1
                                   """, submission_id, admin_note)

                # Give reward (100 XP and 50 coins per quest)
                await conn.execute("""
                                   UPDATE users
                                   SET xp           = xp + 100,
                                       coins        = coins + 50,
                                       total_quests = total_quests + 1
                                   WHERE user_id = $1
                                   """, submission['user_id'])

                # Update level based on XP
                # Level formula: level = 1 + floor(xp / 100)
                await conn.execute("""
                                   UPDATE users
                                   SET level = 1 + (xp / 100)
                                   WHERE user_id = $1
                                   """, submission['user_id'])

                # Update daily quest count
                await conn.execute("""
                                   INSERT INTO daily_quests (user_id, quests_count)
                                   VALUES ($1, 1) ON CONFLICT (user_id, quest_date) 
                    DO
                                   UPDATE SET quests_count = daily_quests.quests_count + 1
                                   """, submission['user_id'])

                return True
        return False

    async def reject_quest(self, submission_id, admin_note=None):
        """Reject quest submission"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               UPDATE quest_submissions
                               SET status     = 'rejected',
                                   admin_note = $2
                               WHERE id = $1
                               """, submission_id, admin_note)
            return True

    # Add these functions to your Database class in database.py

    async def get_leaderboard(self, limit=10, sort_by="xp"):
        """Get top users by XP, coins, or quests"""
        async with self.pool.acquire() as conn:
            if sort_by == "xp":
                users = await conn.fetch("""
                                         SELECT user_id, username, first_name, xp, coins, total_quests
                                         FROM users
                                         ORDER BY xp DESC
                                             LIMIT $1
                                         """, limit)
            elif sort_by == "coins":
                users = await conn.fetch("""
                                         SELECT user_id, username, first_name, xp, coins, total_quests
                                         FROM users
                                         ORDER BY coins DESC
                                             LIMIT $1
                                         """, limit)
            elif sort_by == "quests":
                users = await conn.fetch("""
                                         SELECT user_id, username, first_name, xp, coins, total_quests
                                         FROM users
                                         ORDER BY total_quests DESC
                                             LIMIT $1
                                         """, limit)
            else:
                users = await conn.fetch("""
                                         SELECT user_id, username, first_name, xp, coins, total_quests
                                         FROM users
                                         ORDER BY xp DESC
                                             LIMIT $1
                                         """, limit)

            return users

    async def get_user_rank(self, user_id, sort_by="xp"):
        """Get user's rank in leaderboard"""
        async with self.pool.acquire() as conn:
            if sort_by == "xp":
                rank = await conn.fetchval("""
                                           SELECT COUNT(*) + 1
                                           FROM users
                                           WHERE xp > (SELECT xp FROM users WHERE user_id = $1)
                                           """, user_id)
            elif sort_by == "coins":
                rank = await conn.fetchval("""
                                           SELECT COUNT(*) + 1
                                           FROM users
                                           WHERE coins > (SELECT coins FROM users WHERE user_id = $1)
                                           """, user_id)
            elif sort_by == "quests":
                rank = await conn.fetchval("""
                                           SELECT COUNT(*) + 1
                                           FROM users
                                           WHERE total_quests > (SELECT total_quests FROM users WHERE user_id = $1)
                                           """, user_id)
            else:
                rank = await conn.fetchval("""
                                           SELECT COUNT(*) + 1
                                           FROM users
                                           WHERE xp > (SELECT xp FROM users WHERE user_id = $1)
                                           """, user_id)

            return rank if rank else 1

    async def get_daily_top_users(self, limit=3):
        """Get top users by quests completed today"""
        async with self.pool.acquire() as conn:
            users = await conn.fetch("""
                                     SELECT u.user_id, u.username, u.first_name, d.quests_count
                                     FROM daily_quests d
                                              JOIN users u ON d.user_id = u.user_id
                                     WHERE d.quest_date = CURRENT_DATE
                                     ORDER BY d.quests_count DESC
                                         LIMIT $1
                                     """, limit)
            return users

# Create global database instance
db = Database()