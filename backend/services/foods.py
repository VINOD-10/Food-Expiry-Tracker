"""Inventory CRUD, expiry alerts and dashboard summaries."""
from ..db import transaction, utc_now
from ..errors import Conflict, InvalidInput, NotFound
from ..expiry_engine import ALERT_STATUSES, evaluate, parse_stored_date

# Matches the storage format and default times used by the desktop app.
MFG_TIME = "T12:00:00"
EXPIRY_TIME = "T23:59:00"
SORT_KEYS = {
    "expiry": lambda item: (item["days_remaining"] is None, item["days_remaining"] or 0, item["food_name"].casefold()),
    "newest": lambda item: (-(item["id"]),),
    "name": lambda item: (item["food_name"].casefold(), item["id"]),
}
LEGACY_SORTS = {"Expiry date": "expiry", "Newest": "newest", "Name": "name"}


def serialize(row, today, threshold):
    expiry = parse_stored_date(row["expires_at"] or row["expiry_date"])
    mfg = parse_stored_date(row["mfg_date"])
    return {
        "id": row["id"],
        "food_name": row["food_name"] or "Unnamed item",
        "category": row["category"] or "Other",
        "quantity": row["quantity"],
        "unit": row["unit"],
        "mfg_date": mfg.isoformat() if mfg else None,
        "expiry_date": expiry.isoformat() if expiry else None,
        "storage_location": row["storage_location"],
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **evaluate(expiry, today, threshold),
    }


def _all(conn, today, threshold, search=None, category=None):
    sql, params = "SELECT * FROM food WHERE 1=1", []
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND food_name LIKE ? ESCAPE '\\'"
        params.append(f"%{escaped}%")
    if category:
        sql += " AND category = ?"
        params.append(category)
    return [serialize(row, today, threshold) for row in conn.execute(sql, params)]


def list_foods(conn, today, threshold, search=None, category=None, status=None, sort="expiry", page=1, page_size=20):
    items = _all(conn, today, threshold, search, category)
    if status == "attention":
        items = [item for item in items if item["status"] in ALERT_STATUSES]
    elif status:
        items = [item for item in items if item["status"] == status]
    items.sort(key=SORT_KEYS[sort])
    total = len(items)
    pages = max(1, -(-total // page_size))
    page = min(page, pages)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size, "pages": pages}


def _row(conn, food_id):
    row = conn.execute("SELECT * FROM food WHERE id = ?", (food_id,)).fetchone()
    if row is None:
        raise NotFound(f"Food item {food_id} was not found")
    return row


def get_food(conn, food_id, today, threshold):
    return serialize(_row(conn, food_id), today, threshold)


def _check_mfg(data, today):
    if data.mfg_date and data.mfg_date > today:
        raise InvalidInput("Manufacturing date cannot be in the future", field="mfg_date")


def replayed_id(conn, key, resource):
    if not key:
        return None
    row = conn.execute(
        "SELECT resource_id FROM idempotency_keys WHERE idempotency_key = ? AND resource = ?", (key, resource)
    ).fetchone()
    return row[0] if row else None


def remember_key(conn, key, resource, resource_id):
    if key:
        conn.execute(
            "INSERT OR REPLACE INTO idempotency_keys(idempotency_key, resource, resource_id, created_at) VALUES (?, ?, ?, ?)",
            (key, resource, resource_id, utc_now()),
        )


def insert_food(conn, data, today):
    """Insert inside the caller's transaction and return the new id."""
    _check_mfg(data, today)
    mfg = data.mfg_date.isoformat() + MFG_TIME if data.mfg_date else None
    expires = data.expiry_date.isoformat() + EXPIRY_TIME
    cursor = conn.execute(
        """INSERT INTO food(food_name, mfg_date, expiry_date, purchased_at, expires_at, category,
                            quantity, unit, storage_location, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.food_name, mfg, expires, mfg or today.isoformat() + MFG_TIME, expires, data.category,
         data.quantity, data.unit, data.storage_location, data.notes, utc_now()),
    )
    return cursor.lastrowid


def create_food(conn, data, today, threshold, idempotency_key=None):
    """Returns (item, created). A repeated idempotency key returns the original item."""
    with transaction(conn):
        existing = replayed_id(conn, idempotency_key, "food")
        if existing and conn.execute("SELECT 1 FROM food WHERE id = ?", (existing,)).fetchone():
            return get_food(conn, existing, today, threshold), False
        food_id = insert_food(conn, data, today)
        remember_key(conn, idempotency_key, "food", food_id)
    return get_food(conn, food_id, today, threshold), True


def update_food(conn, food_id, data, today, threshold):
    _check_mfg(data, today)
    with transaction(conn):
        _row(conn, food_id)
        mfg = data.mfg_date.isoformat() + MFG_TIME if data.mfg_date else None
        expires = data.expiry_date.isoformat() + EXPIRY_TIME
        conn.execute(
            """UPDATE food SET food_name = ?, mfg_date = ?, expiry_date = ?, expires_at = ?,
                   purchased_at = COALESCE(?, purchased_at), category = ?, quantity = ?, unit = ?,
                   storage_location = ?, notes = ?
               WHERE id = ?""",
            (data.food_name, mfg, expires, expires, mfg, data.category, data.quantity, data.unit,
             data.storage_location, data.notes, food_id),
        )
    return get_food(conn, food_id, today, threshold)


def delete_food(conn, food_id, reason, today, threshold):
    with transaction(conn):
        item = serialize(_row(conn, food_id), today, threshold)
        conn.execute(
            """INSERT INTO food_removals(food_id, food_name, category, expiry_date, reason, was_expired, removed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (food_id, item["food_name"], item["category"], item["expiry_date"], reason,
             int(item["status"] == "expired"), utc_now()),
        )
        conn.execute("DELETE FROM food WHERE id = ?", (food_id,))
    return item


# -----------------------------
# Alerts
# -----------------------------
def _dismissed(conn):
    return {(row[0], row[1], row[2]) for row in conn.execute("SELECT food_id, status, expiry_date FROM alert_dismissals")}


def list_alerts(conn, today, threshold, include_dismissed=False):
    dismissed = _dismissed(conn)
    alerts = [item for item in _all(conn, today, threshold) if item["status"] in ALERT_STATUSES]
    for item in alerts:
        item["dismissed"] = (item["id"], item["status"], item["expiry_date"]) in dismissed
    alerts.sort(key=SORT_KEYS["expiry"])
    active = [item for item in alerts if not item["dismissed"]]
    counts = {status: sum(item["status"] == status for item in active) for status in ALERT_STATUSES}
    return {
        "items": alerts if include_dismissed else active,
        "counts": counts,
        "active": len(active),
        "dismissed": len(alerts) - len(active),
        "threshold": threshold,
        "today": today.isoformat(),
    }


def dismiss_alert(conn, food_id, today, threshold):
    item = get_food(conn, food_id, today, threshold)
    if item["status"] not in ALERT_STATUSES:
        raise Conflict(f"{item['food_name']} has no active expiry alert")
    conn.execute(
        "INSERT OR IGNORE INTO alert_dismissals(food_id, status, expiry_date, dismissed_at) VALUES (?, ?, ?, ?)",
        (food_id, item["status"], item["expiry_date"], utc_now()),
    )
    return {**item, "dismissed": True}


def restore_alert(conn, food_id, today, threshold):
    item = get_food(conn, food_id, today, threshold)
    conn.execute("DELETE FROM alert_dismissals WHERE food_id = ?", (food_id,))
    return {**item, "dismissed": False}


# -----------------------------
# Dashboard
# -----------------------------
def dashboard(conn, today, threshold):
    items = _all(conn, today, threshold)
    counts = {status: sum(item["status"] == status for item in items) for status in ("safe", "soon", "today", "expired", "unknown")}
    attention = sorted((item for item in items if item["status"] in ALERT_STATUSES), key=SORT_KEYS["expiry"])
    recent = sorted(items, key=lambda item: (item["created_at"] or "", item["id"]), reverse=True)[:5]
    dismissed = _dismissed(conn)
    active_alerts = sum((item["id"], item["status"], item["expiry_date"]) not in dismissed for item in attention)
    return {
        "today": today.isoformat(),
        "threshold": threshold,
        "counts": {**counts, "total": len(items), "expiring": counts["soon"] + counts["today"]},
        "attention": attention[:6],
        "attention_total": len(attention),
        "active_alerts": active_alerts,
        "recent": recent,
    }
