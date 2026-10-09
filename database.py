import os
import time
import logging
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _get_cursor(conn):
    return conn.cursor()

def db_health_check():
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception as e:
        logging.error(f"DB health check failed: {e}")
        return False

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at REAL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_emoji (
            chat_id INTEGER PRIMARY KEY,
            emoji TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            invoice_num TEXT PRIMARY KEY,
            chat_id INTEGER,
            product TEXT,
            amount REAL,
            crypto_amount TEXT,
            crypto_symbol TEXT,
            method TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating INTEGER,
            amount REAL,
            product TEXT,
            review_text TEXT,
            date_time TEXT,
            page_number INTEGER DEFAULT 1,
            added_at REAL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            sender TEXT,
            message TEXT,
            timestamp REAL DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            item_name TEXT,
            added_at REAL DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    logging.info("✅ Database initialised (SQLite)")

# ── Users ──────────────────────────────────────────────────────────────────────

def db_register_user(chat_id, username="", first_name="", last_name=""):
    try:
        conn = get_db_connection()
        conn.execute(
            """INSERT INTO users (chat_id, username, first_name, last_name, registered_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET
                   username=excluded.username,
                   first_name=excluded.first_name,
                   last_name=excluded.last_name""",
            (chat_id, username, first_name, last_name, time.time())
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"db_register_user error: {e}")
        return False

def db_user_exists(chat_id):
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT 1 FROM users WHERE chat_id = ?", (chat_id,)).fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        logging.error(f"db_user_exists error: {e}")
        return False

def db_get_user(chat_id):
    try:
        conn = get_db_connection()
        row = conn.execute(
            "SELECT chat_id, username, first_name, last_name, registered_at FROM users WHERE chat_id = ?",
            (chat_id,)
        ).fetchone()
        conn.close()
        return tuple(row) if row else None
    except Exception as e:
        logging.error(f"db_get_user error: {e}")
        return None

def db_get_user_emoji(chat_id):
    try:
        conn = get_db_connection()
        row = conn.execute("SELECT emoji FROM user_emoji WHERE chat_id = ?", (chat_id,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"db_get_user_emoji error: {e}")
        return None

def db_get_all_user_ids():
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT chat_id FROM users").fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception as e:
        logging.error(f"db_get_all_user_ids error: {e}")
        return []

def db_user_count():
    try:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logging.error(f"db_user_count error: {e}")
        return 0

# ── Orders ─────────────────────────────────────────────────────────────────────

def db_get_pending_orders(chat_id=None):
    try:
        conn = get_db_connection()
        if chat_id:
            rows = conn.execute(
                "SELECT invoice_num, chat_id, product, amount, crypto_amount, crypto_symbol, method, status, created_at "
                "FROM orders WHERE chat_id = ? AND status = 'pending' ORDER BY created_at DESC",
                (chat_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT invoice_num, chat_id, product, amount, crypto_amount, crypto_symbol, method, status, created_at "
                "FROM orders WHERE status = 'pending' ORDER BY created_at DESC"
            ).fetchall()
        conn.close()
        return [tuple(r) for r in rows]
    except Exception as e:
        logging.error(f"db_get_pending_orders error: {e}")
        return []

# ── Reviews ────────────────────────────────────────────────────────────────────

def db_add_review(rating, amount, product, review_text, date_time):
    try:
        conn = get_db_connection()
        total = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        page_number = (total // 10) + 1
        conn.execute(
            "INSERT INTO reviews (rating, amount, product, review_text, date_time, page_number, added_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (rating, amount, product, review_text, date_time, page_number, time.time())
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"db_add_review error: {e}")
        return False

def db_get_reviews(page_number=1, per_page=10):
    try:
        conn = get_db_connection()
        offset = (page_number - 1) * per_page
        rows = conn.execute(
            "SELECT rating, amount, product, review_text, date_time FROM reviews "
            "ORDER BY added_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        ).fetchall()
        conn.close()
        return [tuple(r) for r in rows]
    except Exception as e:
        logging.error(f"db_get_reviews error: {e}")
        return []

# ── Wishlist ───────────────────────────────────────────────────────────────────

def db_get_wishlist(chat_id):
    try:
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT id, item_name FROM wishlist WHERE chat_id = ? ORDER BY added_at ASC",
            (chat_id,)
        ).fetchall()
        conn.close()
        return [tuple(r) for r in rows]
    except Exception as e:
        logging.error(f"db_get_wishlist error: {e}")
        return []

def db_add_wishlist_item(chat_id, item_name):
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO wishlist (chat_id, item_name, added_at) VALUES (?, ?, ?)",
            (chat_id, item_name, time.time())
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"db_add_wishlist_item error: {e}")
        return False

def db_remove_wishlist_item(chat_id, item_id):
    try:
        conn = get_db_connection()
        conn.execute(
            "DELETE FROM wishlist WHERE id = ? AND chat_id = ?",
            (item_id, chat_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"db_remove_wishlist_item error: {e}")
        return False
