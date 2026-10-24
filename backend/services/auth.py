"""Accounts, password hashing and cookie sessions (standard library only)."""
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from ..db import transaction, utc_now
from ..errors import AppError, Conflict, InvalidInput

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2 ** 14, 8, 1
MAX_FAILURES_PER_EMAIL = 5
MAX_FAILURES_PER_IP = 30
FAILURE_WINDOW = timedelta(minutes=15)
INVALID_LOGIN = "Incorrect email or password"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class TooManyAttempts(AppError):
    status_code = 429
    code = "too_many_attempts"


class SignupClosed(AppError):
    status_code = 403
    code = "signup_closed"


def _b64(raw):
    return base64.b64encode(raw).decode()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password, stored):
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# Verifying against this when the email is unknown keeps response times similar,
# so timing does not reveal which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def public_user(row, owner_id=None):
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "created_at": row["created_at"],
        "is_owner": row["id"] == owner_id,
        "has_recovery_code": bool(row["recovery_hash"]) if "recovery_hash" in row.keys() else False,
    }


def owner_id(conn):
    return conn.execute("SELECT min(id) FROM users").fetchone()[0]


def create_session(conn, user_id, days):
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    conn.execute(
        "INSERT INTO sessions(token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_token_hash(token), user_id, _iso(now), _iso(now + timedelta(days=days))),
    )
    return token


def user_for_token(conn, token):
    if not token:
        return None
    row = conn.execute(
        """SELECT users.* FROM sessions JOIN users ON users.id = sessions.user_id
           WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
        (_token_hash(token), utc_now()),
    ).fetchone()
    return row


def end_session(conn, token):
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


# Recovery codes: 20 characters from an alphabet without look-alikes (no 0/O, 1/I/L),
# about 100 bits of randomness, shown once and stored only as a scrypt hash.
RECOVERY_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVALID_RECOVERY = "That email and recovery code don't match"


def new_recovery_code():
    raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(20))
    return "-".join(raw[i:i + 5] for i in range(0, 20, 5))


def _normalise_code(code):
    return "".join(ch for ch in code.upper() if ch.isalnum())


def _set_recovery_code(conn, user_id):
    code = new_recovery_code()
    conn.execute("UPDATE users SET recovery_hash = ? WHERE id = ?", (hash_password(_normalise_code(code)), user_id))
    return code


def regenerate_recovery_code(conn, user_id, password):
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not verify_password(password, row["password_hash"]):
        raise InvalidInput("Your password is incorrect", field="password")
    with transaction(conn):
        return _set_recovery_code(conn, user_id)


def reset_with_recovery_code(conn, email, code, new_password, ip, days):
    """Forgot-password flow. The code is single-use: a fresh one is issued with the new password.
    Returns (user_row, session_token, new_recovery_code)."""
    email = email.strip().lower()
    _check_throttle(conn, email, ip)
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    stored = row["recovery_hash"] if row and row["recovery_hash"] else _DUMMY_HASH
    if not verify_password(_normalise_code(code), stored) or row is None or not row["recovery_hash"]:
        with transaction(conn):
            conn.execute("INSERT INTO auth_failures(email, ip, attempted_at) VALUES (?, ?, ?)", (email, ip, utc_now()))
        raise Unauthorized(INVALID_RECOVERY)
    with transaction(conn):
        conn.execute("UPDATE users SET password_hash = ?, last_login_at = ? WHERE id = ?", (hash_password(new_password), utc_now(), row["id"]))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))  # sign out everywhere
        conn.execute("DELETE FROM auth_failures WHERE email = ?", (email,))
        new_code = _set_recovery_code(conn, row["id"])
        token = create_session(conn, row["id"], days)
    return row, token, new_code


def set_password_directly(conn, email, new_password):
    """For the server operator (python -m backend.manage). Signs the user out everywhere."""
    with transaction(conn):
        row = conn.execute("SELECT id FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        if row is None:
            return False
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), row["id"]))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))
    return True


def register(conn, data, session_days, allow_signup):
    """Create an account and return (user_row, token, recovery_code). The first account becomes the owner."""
    with transaction(conn):
        first = owner_id(conn) is None
        if not allow_signup and not first:
            raise SignupClosed("New accounts are disabled on this server. Ask the owner to create one for you.")
        if conn.execute("SELECT 1 FROM users WHERE email = ?", (data.email,)).fetchone():
            raise Conflict("An account with this email already exists. Try logging in instead.", field="email")
        now = utc_now()
        user_id = conn.execute(
            "INSERT INTO users(email, display_name, password_hash, created_at, last_login_at) VALUES (?, ?, ?, ?, ?)",
            (data.email, data.display_name, hash_password(data.password), now, now),
        ).lastrowid
        if first:
            _claim_existing_data(conn, user_id)
        recovery_code = _set_recovery_code(conn, user_id)
        token = create_session(conn, user_id, session_days)
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone(), token, recovery_code


def _claim_existing_data(conn, user_id):
    """The owner takes over everything created before accounts existed."""
    for table in ("food", "shopping_items", "food_removals"):
        conn.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (user_id,))
    conn.execute(
        "INSERT OR IGNORE INTO user_settings(user_id, setting_key, setting_value) SELECT ?, setting_key, setting_value FROM settings",
        (user_id,),
    )


def _check_throttle(conn, email, ip):
    since = _iso(datetime.now(timezone.utc) - FAILURE_WINDOW)
    by_email = conn.execute("SELECT count(*) FROM auth_failures WHERE email = ? AND attempted_at > ?", (email, since)).fetchone()[0]
    by_ip = conn.execute("SELECT count(*) FROM auth_failures WHERE ip = ? AND attempted_at > ?", (ip, since)).fetchone()[0]
    if by_email >= MAX_FAILURES_PER_EMAIL or by_ip >= MAX_FAILURES_PER_IP:
        raise TooManyAttempts("Too many failed attempts. Please wait 15 minutes and try again.")


def login(conn, email, password, ip, days):
    email = email.strip().lower()
    _check_throttle(conn, email, ip)
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not verify_password(password, row["password_hash"] if row else _DUMMY_HASH) or row is None:
        with transaction(conn):
            conn.execute("INSERT INTO auth_failures(email, ip, attempted_at) VALUES (?, ?, ?)", (email, ip, utc_now()))
            conn.execute("DELETE FROM auth_failures WHERE attempted_at < ?", (_iso(datetime.now(timezone.utc) - timedelta(days=1)),))
        raise Unauthorized(INVALID_LOGIN)
    with transaction(conn):
        conn.execute("DELETE FROM auth_failures WHERE email = ?", (email,))
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND expires_at <= ?", (row["id"], utc_now()))
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utc_now(), row["id"]))
        token = create_session(conn, row["id"], days)
    return row, token


def change_password(conn, user_id, current, new, keep_token):
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not verify_password(current, row["password_hash"]):
        raise InvalidInput("Your current password is incorrect", field="current_password")
    with transaction(conn):
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), user_id))
        # Sign out every other device; keep the session that made the change.
        conn.execute("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user_id, _token_hash(keep_token)))
