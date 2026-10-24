import sqlite3
from pathlib import Path

from expiry import parse_datetime, STORAGE_FORMAT


DATABASE_PATH = Path(__file__).resolve().with_name("food.db")


def _connect():
    return sqlite3.connect(DATABASE_PATH)


def _owner_filter(cursor):
    """The desktop app has no login: it shows the owner's data (the first web account).
    Rows with no owner yet (before any account exists) stay visible too."""
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(food)")}
    has_users = cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
    if "user_id" in columns and has_users:
        return " AND (user_id IS NULL OR user_id = (SELECT min(id) FROM users))"
    return ""

# -----------------------------
# Create database and table
# -----------------------------
def connect():

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_name TEXT,
        mfg_date TEXT,
        expiry_date TEXT,
        purchased_at TEXT,
        expires_at TEXT
    )
    """)
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(food)")}
    if "purchased_at" not in columns:
        cursor.execute("ALTER TABLE food ADD COLUMN purchased_at TEXT")
    if "expires_at" not in columns:
        cursor.execute("ALTER TABLE food ADD COLUMN expires_at TEXT")
    cursor.execute("SELECT id, mfg_date, expiry_date FROM food WHERE purchased_at IS NULL OR expires_at IS NULL")
    for food_id, mfg_date, expiry_date in cursor.fetchall():
        try:
            cursor.execute(
                "UPDATE food SET purchased_at=?, expires_at=? WHERE id=?",
                (parse_datetime(mfg_date).strftime(STORAGE_FORMAT), parse_datetime(expiry_date).strftime(STORAGE_FORMAT), food_id),
            )
        except ValueError:
            continue

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL
    )
    """)
    defaults = {
        "expiry_threshold": "3",
        "date_format": "%d-%m-%Y",
        "default_sort": "Expiry date",
    }
    for key, value in defaults.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings(setting_key, setting_value) VALUES (?, ?)",
            (key, value),
        )

    conn.commit()
    conn.close()


# -----------------------------
# Insert food
# -----------------------------
def insert(food_name, mfg_date, expiry_date):

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO food(food_name, mfg_date, expiry_date, purchased_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (food_name, mfg_date, expiry_date, mfg_date, expiry_date)
    )

    conn.commit()
    conn.close()


# -----------------------------
# Fetch all records
# -----------------------------
def fetch():

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("SELECT id, food_name, mfg_date, expiry_date, purchased_at, expires_at FROM food WHERE 1=1" + _owner_filter(cursor) + " ORDER BY id ASC")

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Search food
# -----------------------------
def search(food_name):

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM food WHERE food_name LIKE ?" + _owner_filter(cursor),
        ('%' + food_name + '%',)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Delete one food
# -----------------------------
def delete(food_id, reason=None, was_expired=False):

    conn = _connect()
    cursor = conn.cursor()

    # Record why the item left the inventory, for the web app's waste insights.
    # The food_removals table only exists once the web app has migrated the database.
    has_history = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='food_removals'"
    ).fetchone()
    if reason and has_history:
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(food)")}
        category = "category" if "category" in columns else "NULL"
        cursor.execute(
            f"""INSERT INTO food_removals(food_id, food_name, category, expiry_date, reason, was_expired, removed_at)
                SELECT id, COALESCE(food_name, 'Unnamed item'), {category}, substr(COALESCE(expires_at, expiry_date), 1, 10),
                       ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
                FROM food WHERE id=?""" + _owner_filter(cursor),
            (reason, int(was_expired), food_id),
        )

    cursor.execute(
        "DELETE FROM food WHERE id=?" + _owner_filter(cursor),
        (food_id,)
    )

    conn.commit()
    conn.close()


# -----------------------------
# Delete all foods
# -----------------------------
def delete_all():

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM food WHERE 1=1" + _owner_filter(cursor))

    conn.commit()
    conn.close()
def update(food_id, food_name, mfg_date, expiry_date):

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE food
        SET food_name=?, mfg_date=?, expiry_date=?, purchased_at=?, expires_at=?
        WHERE id=?""" + _owner_filter(cursor), (food_name, mfg_date, expiry_date, mfg_date, expiry_date, food_id))

    conn.commit()
    conn.close()


def get_settings():
    conn = _connect()
    settings = dict(conn.execute("SELECT setting_key, setting_value FROM settings").fetchall())
    # Once accounts exist, the owner's own settings (edited in the web app) take priority.
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_settings'").fetchone():
        settings.update(conn.execute(
            "SELECT setting_key, setting_value FROM user_settings WHERE user_id = (SELECT min(id) FROM users)"
        ).fetchall())
    conn.close()
    return settings


def save_settings(settings):
    conn = _connect()
    conn.executemany(
        "INSERT OR REPLACE INTO settings(setting_key, setting_value) VALUES (?, ?)",
        settings.items(),
    )
    conn.commit()
    conn.close()