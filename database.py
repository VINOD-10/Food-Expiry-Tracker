import sqlite3
from pathlib import Path

from expiry import parse_datetime, STORAGE_FORMAT


DATABASE_PATH = Path(__file__).resolve().with_name("food.db")


def _connect():
    return sqlite3.connect(DATABASE_PATH)

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

    cursor.execute("SELECT id, food_name, mfg_date, expiry_date, purchased_at, expires_at FROM food ORDER BY id ASC")

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
        "SELECT * FROM food WHERE food_name LIKE ?",
        ('%' + food_name + '%',)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


# -----------------------------
# Delete one food
# -----------------------------
def delete(food_id):

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM food WHERE id=?",
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

    cursor.execute("DELETE FROM food")

    conn.commit()
    conn.close()
def update(food_id, food_name, mfg_date, expiry_date):

    conn = _connect()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE food
        SET food_name=?, mfg_date=?, expiry_date=?, purchased_at=?, expires_at=?
        WHERE id=?
    """, (food_name, mfg_date, expiry_date, mfg_date, expiry_date, food_id))

    conn.commit()
    conn.close()


def get_settings():
    conn = _connect()
    rows = conn.execute("SELECT setting_key, setting_value FROM settings").fetchall()
    conn.close()
    return dict(rows)


def save_settings(settings):
    conn = _connect()
    conn.executemany(
        "INSERT OR REPLACE INTO settings(setting_key, setting_value) VALUES (?, ?)",
        settings.items(),
    )
    conn.commit()
    conn.close()