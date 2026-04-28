import aiosqlite
import datetime

DB_PATH = "roulette.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 1000,
                is_blocked INTEGER DEFAULT 0,
                total_bets INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                total_wagered REAL DEFAULT 0,
                total_won REAL DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bet_type TEXT,
                bet_value TEXT,
                amount REAL,
                result_number INTEGER,
                win REAL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                amount REAL,
                max_uses INTEGER,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo_uses (
                user_id INTEGER,
                code TEXT,
                PRIMARY KEY (user_id, code)
            )
        """)
        # Default settings
        await db.execute("INSERT OR IGNORE INTO settings VALUES ('min_bet', '10')")
        await db.execute("INSERT OR IGNORE INTO settings VALUES ('max_bet', '10000')")
        await db.commit()

# ─── USER ───────────────────────────────────────────────

async def get_or_create_user(user_id, username, full_name):
    from config import START_BALANCE
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, balance) VALUES (?,?,?,?)",
                (user_id, username, full_name, START_BALANCE)
            )
            await db.commit()
        else:
            await db.execute(
                "UPDATE users SET username=?, full_name=? WHERE user_id=?",
                (username, full_name, user_id)
            )
            await db.commit()
    return await get_user(user_id)

async def get_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def update_balance(user_id, delta):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (delta, user_id))
        await db.commit()

async def set_balance(user_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, user_id))
        await db.commit()

async def block_user(user_id, block=True):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_blocked=? WHERE user_id=?", (1 if block else 0, user_id))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY balance DESC") as cur:
            return await cur.fetchall()

async def get_top_users(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users ORDER BY total_won DESC LIMIT ?", (limit,)) as cur:
            return await cur.fetchall()

# ─── BETS ───────────────────────────────────────────────

async def save_bet(user_id, bet_type, bet_value, amount, result_number, win):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO bets (user_id, bet_type, bet_value, amount, result_number, win) VALUES (?,?,?,?,?,?)",
            (user_id, bet_type, bet_value, amount, result_number, win)
        )
        won = win > 0
        await db.execute("""
            UPDATE users SET
                total_bets = total_bets + 1,
                total_wins = total_wins + ?,
                total_losses = total_losses + ?,
                total_wagered = total_wagered + ?,
                total_won = total_won + ?
            WHERE user_id=?
        """, (1 if won else 0, 0 if won else 1, amount, win, user_id))
        await db.commit()

async def get_user_bets(user_id, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM bets WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, limit)
        ) as cur:
            return await cur.fetchall()

async def get_all_bets(limit=50):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT b.*, u.username FROM bets b JOIN users u ON b.user_id=u.user_id ORDER BY b.id DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()

async def get_global_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT 
                COUNT(DISTINCT user_id) as total_users,
                COUNT(*) as total_bets,
                SUM(amount) as total_wagered,
                SUM(win) as total_paid,
                SUM(amount) - SUM(win) as profit
            FROM bets
        """) as cur:
            return await cur.fetchone()

# ─── SETTINGS ───────────────────────────────────────────

async def get_setting(key):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, str(value)))
        await db.commit()

# ─── PROMOCODES ─────────────────────────────────────────

async def create_promo(code, amount, max_uses):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO promocodes (code, amount, max_uses) VALUES (?,?,?)",
            (code.upper(), amount, max_uses)
        )
        await db.commit()

async def use_promo(user_id, code):
    code = code.upper()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promocodes WHERE code=?", (code,)) as cur:
            promo = await cur.fetchone()
        if not promo:
            return None, "❌ Промокод не найден"
        if not promo["is_active"]:
            return None, "❌ Промокод деактивирован"
        if promo["used_count"] >= promo["max_uses"]:
            return None, "❌ Промокод исчерпан"
        async with db.execute("SELECT 1 FROM promo_uses WHERE user_id=? AND code=?", (user_id, code)) as cur:
            if await cur.fetchone():
                return None, "❌ Ты уже использовал этот промокод"
        await db.execute("UPDATE promocodes SET used_count=used_count+1 WHERE code=?", (code,))
        await db.execute("INSERT INTO promo_uses VALUES (?,?)", (user_id, code))
        await db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (promo["amount"], user_id))
        await db.commit()
        return promo["amount"], "✅ Успешно"

async def get_all_promos():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM promocodes ORDER BY created_at DESC") as cur:
            return await cur.fetchall()

async def deactivate_promo(code):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE promocodes SET is_active=0 WHERE code=?", (code.upper(),))
        await db.commit()
