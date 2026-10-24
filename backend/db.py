"""SQLite connection handling shared by every request."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def connect(database_path):
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
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
