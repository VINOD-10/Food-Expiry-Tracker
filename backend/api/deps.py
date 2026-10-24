"""Shared request dependencies."""
import re

from fastapi import Depends, Header, Request

from ..db import connect
from ..errors import InvalidInput
from ..expiry_engine import today_in
from ..services.settings import threshold as stored_threshold

IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def get_conn(request: Request):
    conn = connect(request.app.state.settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


def get_today(request: Request):
    return today_in(request.app.state.settings.timezone)


def get_threshold(conn=Depends(get_conn)):
    return stored_threshold(conn)


def get_idempotency_key(idempotency_key: str | None = Header(default=None)):
    if idempotency_key is not None and not IDEMPOTENCY_PATTERN.match(idempotency_key):
        raise InvalidInput("Idempotency-Key must be 8-128 letters, digits, '-' or '_'")
    return idempotency_key
