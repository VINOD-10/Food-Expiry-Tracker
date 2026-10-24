"""Shopping list CRUD and transfer of purchased items into inventory."""
from pydantic import ValidationError

from ..db import transaction, utc_now
from ..errors import Conflict, InvalidInput, NotFound
from ..schemas import FoodIn
from . import foods


def _serialize(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "quantity": row["quantity"],
        "unit": row["unit"],
        "category": row["category"],
        "notes": row["notes"],
        "purchased": bool(row["purchased"]),
        "purchased_at": row["purchased_at"],
        "inventory_food_id": row["inventory_food_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row(conn, item_id):
    row = conn.execute("SELECT * FROM shopping_items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise NotFound(f"Shopping item {item_id} was not found")
    return row


def list_items(conn, status="all"):
    sql = "SELECT * FROM shopping_items"
    if status == "pending":
        sql += " WHERE purchased = 0"
    elif status == "purchased":
        sql += " WHERE purchased = 1"
    rows = conn.execute(sql + " ORDER BY purchased ASC, id DESC").fetchall()
    pending, purchased = conn.execute(
        "SELECT COALESCE(SUM(purchased = 0), 0), COALESCE(SUM(purchased = 1), 0) FROM shopping_items"
    ).fetchone()
    return {"items": [_serialize(row) for row in rows], "counts": {"pending": pending, "purchased": purchased, "all": pending + purchased}}


def create_item(conn, data, idempotency_key=None):
    with transaction(conn):
        existing = foods.replayed_id(conn, idempotency_key, "shopping")
        if existing and conn.execute("SELECT 1 FROM shopping_items WHERE id = ?", (existing,)).fetchone():
            return _serialize(_row(conn, existing)), False
        now = utc_now()
        cursor = conn.execute(
            "INSERT INTO shopping_items(name, quantity, unit, category, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (data.name, data.quantity, data.unit, data.category, data.notes, now, now),
        )
        foods.remember_key(conn, idempotency_key, "shopping", cursor.lastrowid)
    return _serialize(_row(conn, cursor.lastrowid)), True


def update_item(conn, item_id, data):
    with transaction(conn):
        _row(conn, item_id)
        conn.execute(
            "UPDATE shopping_items SET name = ?, quantity = ?, unit = ?, category = ?, notes = ?, updated_at = ? WHERE id = ?",
            (data.name, data.quantity, data.unit, data.category, data.notes, utc_now(), item_id),
        )
    return _serialize(_row(conn, item_id))


def set_status(conn, item_id, purchased):
    with transaction(conn):
        _row(conn, item_id)
        now = utc_now()
        conn.execute(
            "UPDATE shopping_items SET purchased = ?, purchased_at = ?, updated_at = ? WHERE id = ?",
            (int(purchased), now if purchased else None, now, item_id),
        )
    return _serialize(_row(conn, item_id))


def delete_item(conn, item_id):
    with transaction(conn):
        item = _serialize(_row(conn, item_id))
        conn.execute("DELETE FROM shopping_items WHERE id = ?", (item_id,))
    return item


def clear_completed(conn):
    with transaction(conn):
        removed = conn.execute("DELETE FROM shopping_items WHERE purchased = 1").rowcount
    return {"removed": removed}


def move_to_inventory(conn, item_id, data, today, threshold):
    with transaction(conn):
        item = _row(conn, item_id)
        if item["inventory_food_id"] is not None:
            raise Conflict(f"{item['name']} has already been added to your inventory")
        try:
            food = FoodIn(
                food_name=item["name"],
                category=data.category or item["category"],
                quantity=data.quantity or item["quantity"],
                unit=data.unit or item["unit"],
                mfg_date=data.mfg_date,
                expiry_date=data.expiry_date,
                storage_location=data.storage_location,
                notes=item["notes"],
            )
        except ValidationError as error:
            raise InvalidInput(error.errors()[0]["msg"].removeprefix("Value error, ")) from None
        food_id = foods.insert_food(conn, food, today)
        now = utc_now()
        conn.execute(
            "UPDATE shopping_items SET purchased = 1, purchased_at = COALESCE(purchased_at, ?), inventory_food_id = ?, updated_at = ? WHERE id = ?",
            (now, food_id, now, item_id),
        )
    return {"shopping_item": _serialize(_row(conn, item_id)), "food": foods.get_food(conn, food_id, today, threshold)}
