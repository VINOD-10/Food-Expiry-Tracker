import sqlite3

from backend.db import connect
from backend.migrations import MIGRATIONS, migrate

LEGACY_ROWS = [
    (10, "apple", "2026-09-09T12:00:00", "2026-09-10T23:59:00", "2026-09-09T12:00:00", "2026-09-10T23:59:00"),
    (14, "dt", "23-08-2026", "24-08-2026", None, None),
]


def make_legacy_db(path):
    """The exact schema the desktop app produced before this upgrade."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE food(id INTEGER PRIMARY KEY AUTOINCREMENT, food_name TEXT, mfg_date TEXT, expiry_date TEXT,
                          purchased_at TEXT, expires_at TEXT);
        CREATE TABLE settings(setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL);
        INSERT INTO settings VALUES ('expiry_threshold', '5'), ('date_format', '%d-%m-%Y'), ('default_sort', 'Expiry date');
    """)
    conn.executemany("INSERT INTO food VALUES (?, ?, ?, ?, ?, ?)", LEGACY_ROWS)
    conn.commit()
    conn.close()


def test_legacy_database_is_backed_up_and_preserved(tmp_path):
    db_path, backups = tmp_path / "food.db", tmp_path / "backups"
    make_legacy_db(db_path)
    conn = connect(db_path)
    backup = migrate(conn, backups)

    assert backup is not None and backup.exists()
    copy = sqlite3.connect(backup)
    assert copy.execute("SELECT * FROM food ORDER BY id").fetchall() == LEGACY_ROWS
    assert copy.execute("PRAGMA integrity_check").fetchone() == ("ok",)

    rows = conn.execute("SELECT id, food_name, mfg_date, expiry_date, purchased_at, expires_at FROM food ORDER BY id").fetchall()
    assert [tuple(row) for row in rows] == LEGACY_ROWS
    assert conn.execute("SELECT category FROM food").fetchall()[0][0] == "Other"
    settings = dict(conn.execute("SELECT * FROM settings").fetchall())
    assert settings["expiry_threshold"] == "5", "existing settings are not overwritten"
    assert settings["theme"] == "system"
    assert [row[0] for row in conn.execute("SELECT version FROM schema_migrations ORDER BY version")] == [m[0] for m in MIGRATIONS]


def test_migrations_are_idempotent(tmp_path):
    db_path = tmp_path / "food.db"
    make_legacy_db(db_path)
    conn = connect(db_path)
    migrate(conn, tmp_path / "backups")
    assert migrate(conn, tmp_path / "backups") is None
    assert len(list((tmp_path / "backups").iterdir())) == 1


def test_fresh_database_needs_no_backup_and_seeds_no_food(tmp_path):
    conn = connect(tmp_path / "food.db")
    assert migrate(conn, tmp_path / "backups") is None
    assert conn.execute("SELECT count(*) FROM food").fetchone()[0] == 0
    assert not (tmp_path / "backups").exists()


def test_foreign_keys_enabled(tmp_path):
    conn = connect(tmp_path / "food.db")
    migrate(conn, tmp_path / "backups")
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    try:
        conn.execute("INSERT INTO alert_dismissals VALUES (999, 'soon', '2026-10-25', 'now')")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("foreign key was not enforced")


def test_desktop_app_inserts_get_timestamps(tmp_path):
    conn = connect(tmp_path / "food.db")
    migrate(conn, tmp_path / "backups")
    conn.execute("INSERT INTO food(food_name, mfg_date, expiry_date, purchased_at, expires_at) VALUES ('x', 'a', 'b', 'a', 'b')")
    assert conn.execute("SELECT created_at FROM food").fetchone()[0].endswith("Z")
    conn.execute("UPDATE food SET food_name = 'y'")
    assert conn.execute("SELECT updated_at FROM food").fetchone()[0] is not None


def test_failed_migration_rolls_back(tmp_path, monkeypatch):
    import backend.migrations as migrations

    def broken(conn):
        conn.execute("CREATE TABLE half_done(id INTEGER)")
        raise RuntimeError("boom")

    monkeypatch.setattr(migrations, "MIGRATIONS", (*MIGRATIONS, (99, "broken", broken)))
    conn = connect(tmp_path / "food.db")
    try:
        migrations.migrate(conn, tmp_path / "backups")
    except RuntimeError:
        pass
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "half_done" not in tables
    assert 99 not in {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
