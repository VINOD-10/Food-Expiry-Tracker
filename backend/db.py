"""SQLite connection handling shared by every request."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote


class MysqlRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            if key < 0:
                key = len(self) + key
            values = list(self.values())
            if key >= len(values):
                raise IndexError(key)
            return values[key]
        return super().__getitem__(key)

    def keys(self):
        return super().keys()


class MysqlCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        sql = sql.replace("INSERT OR IGNORE INTO", "INSERT IGNORE INTO")
        sql = sql.replace("INSERT OR REPLACE INTO", "REPLACE INTO")
        sql = sql.replace("COLLATE NOCASE", "")
        sql = sql.replace("?", "%s")
        sql = sql.replace(
            "ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value",
            "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)",
        )
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        return self

    def executemany(self, sql, seq):
        sql = sql.replace("INSERT OR IGNORE INTO", "INSERT IGNORE INTO")
        sql = sql.replace("?", "%s")
        sql = sql.replace(
            "ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value",
            "ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)",
        )
        self._cursor.executemany(sql, seq)
        return self

    def fetchone(self):
        row = self._cursor.fetchone()
        return MysqlRow(row) if row else None

    def fetchall(self):
        return [MysqlRow(row) for row in self._cursor.fetchall()]

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class MysqlConnection:
    def __init__(self, database_url):
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError("Install MySQL support with: pip install pymysql") from exc
        url = urlparse(database_url)
        self._conn = pymysql.connect(
            host=url.hostname or "127.0.0.1",
            port=url.port or 3306,
            user=unquote(url.username or "root"),
            password=unquote(url.password or ""),
            database=unquote(url.path.lstrip("/")),
            charset="utf8mb4",
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def execute(self, sql, params=None):
        return MysqlCursor(self._conn.cursor()).execute(sql, params)

    def executemany(self, sql, seq):
        return MysqlCursor(self._conn.cursor()).executemany(sql, seq)

    def cursor(self):
        return MysqlCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def connect(database_path, database_url=None):
    if database_url:
        return MysqlConnection(database_url)
    # FastAPI may open the per-request connection in one worker thread and run the
    # endpoint in another. Each connection still serves exactly one request at a time.
    conn = sqlite3.connect(database_path, timeout=10, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


@contextmanager
def transaction(conn):
    """Run a block atomically; roll back on any error."""
    if isinstance(conn, MysqlConnection):
        conn.execute("START TRANSACTION")
    else:
        conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
