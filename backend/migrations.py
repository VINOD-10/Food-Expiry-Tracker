"""Versioned, additive schema migrations for the existing food.db.

Every migration is recorded in ``schema_migrations``. Before any pending
migration runs against a database that already holds tables, a verified
copy is written to the backup directory using SQLite's online backup API.
Migrations only add tables, columns, indexes and triggers; nothing is
dropped or rewritten, so the desktop app (app.py) keeps working.
"""
import sqlite3
from datetime import datetime

from .db import transaction, utc_now


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_column(conn, table, definition):
    name = definition.split()[0]
    if name not in _columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _baseline(conn):
    # Same tables the desktop app creates in database.connect().
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT,
            mfg_date TEXT,
            expiry_date TEXT,
            purchased_at TEXT,
            expires_at TEXT
        )
    """)
    _add_column(conn, "food", "purchased_at TEXT")
    _add_column(conn, "food", "expires_at TEXT")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
    """)


def _food_details(conn):
    _add_column(conn, "food", "category TEXT NOT NULL DEFAULT 'Other'")
    _add_column(conn, "food", "quantity REAL")
    _add_column(conn, "food", "unit TEXT")
    _add_column(conn, "food", "storage_location TEXT")
    _add_column(conn, "food", "notes TEXT")
    _add_column(conn, "food", "created_at TEXT")
    _add_column(conn, "food", "updated_at TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_food_expires_at ON food(expires_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_food_category ON food(category)")
    # Rows inserted by the desktop app do not set timestamps; fill them in.
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS food_set_created_at AFTER INSERT ON food
        WHEN NEW.created_at IS NULL
        BEGIN
            UPDATE food SET created_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = NEW.id;
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS food_set_updated_at
        AFTER UPDATE OF food_name, mfg_date, expiry_date, purchased_at, expires_at,
                        category, quantity, unit, storage_location, notes ON food
        BEGIN
            UPDATE food SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = NEW.id;
        END
    """)


def _shopping_list(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            quantity REAL CHECK(quantity IS NULL OR quantity > 0),
            unit TEXT,
            category TEXT NOT NULL DEFAULT 'Other',
            notes TEXT,
            purchased INTEGER NOT NULL DEFAULT 0 CHECK(purchased IN (0, 1)),
            purchased_at TEXT,
            inventory_food_id INTEGER REFERENCES food(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shopping_purchased ON shopping_items(purchased)")


def _alerts_and_history(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_dismissals(
            food_id INTEGER NOT NULL REFERENCES food(id) ON DELETE CASCADE,
            status TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            dismissed_at TEXT NOT NULL,
            PRIMARY KEY (food_id, status, expiry_date)
        )
    """)
    # food_id is deliberately not a foreign key: removal history must outlive the item.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS food_removals(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            category TEXT,
            expiry_date TEXT,
            reason TEXT NOT NULL CHECK(reason IN ('consumed', 'discarded', 'other')),
            was_expired INTEGER NOT NULL CHECK(was_expired IN (0, 1)),
            removed_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_food_removals_removed_at ON food_removals(removed_at)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS idempotency_keys(
            idempotency_key TEXT PRIMARY KEY,
            resource TEXT NOT NULL,
            resource_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)


def _setting_defaults(conn):
    defaults = {
        # Keys the desktop app already seeds; kept identical.
        "expiry_threshold": "3",
        "date_format": "%d-%m-%Y",
        "default_sort": "Expiry date",
        # New web settings.
        "theme": "system",
        "browser_notifications": "false",
    }
    conn.executemany(
        "INSERT OR IGNORE INTO settings(setting_key, setting_value) VALUES (?, ?)",
        defaults.items(),
    )


MIGRATIONS = (
    (1, "baseline_desktop_schema", _baseline),
    (2, "food_details_columns", _food_details),
    (3, "shopping_list", _shopping_list),
    (4, "alerts_removals_idempotency", _alerts_and_history),
    (5, "setting_defaults", _setting_defaults),
)


def backup_database(conn, backup_dir, label):
    """Copy the live database with the backup API and verify the copy."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"food-{label}-{datetime.now():%Y%m%d-%H%M%S}.db"
    copy = sqlite3.connect(target)
    try:
        conn.backup(copy)
        if copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"Backup {target} failed its integrity check")
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            original = conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            copied = copy.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            if original != copied:
                raise RuntimeError(f"Backup {target} is missing rows from {table}")
    finally:
        copy.close()
    return target


def migrate(conn, backup_dir):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations(
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    pending = [migration for migration in MIGRATIONS if migration[0] not in applied]
    if not pending:
        return None
    has_data = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT IN ('schema_migrations', 'sqlite_sequence')"
    ).fetchone()[0]
    backup = backup_database(conn, backup_dir, f"pre-migration-v{pending[0][0]}") if has_data else None
    for version, name, apply in pending:
        with transaction(conn):
            apply(conn)
            conn.execute(
                "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, utc_now()),
            )
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("Foreign key check failed after migration")
    return backup
