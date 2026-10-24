"""Shopping list CRUD and transfer of purchased items into inventory (per user)."""
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


def _row(ctx, item_id):
    row = ctx.conn.execute("SELECT * FROM shopping_items WHERE id = ? AND user_id = ?", (item_id, ctx.user_id)).fetchone()
    if row is None:
        raise NotFound(f"Shopping item {item_id} was not found")
    return row


def list_items(ctx, status="all"):
    sql = "SELECT * FROM shopping_items WHERE user_id = ?"
    if status == "pending":
        sql += " AND purchased = 0"
    elif status == "purchased":
        sql += " AND purchased = 1"
    rows = ctx.conn.execute(sql + " ORDER BY purchased ASC, id DESC", (ctx.user_id,)).fetchall()
    pending, purchased = ctx.conn.execute(
        "SELECT COALESCE(SUM(purchased = 0), 0), COALESCE(SUM(purchased = 1), 0) FROM shopping_items WHERE user_id = ?",
        (ctx.user_id,),
    ).fetchone()
    return {"items": [_serialize(row) for row in rows], "counts": {"pending": pending, "purchased": purchased, "all": pending + purchased}}


def create_item(ctx, data, idempotency_key=None):
    with transaction(ctx.conn):
        existing = foods.replayed_id(ctx, idempotency_key, "shopping")
        if existing and ctx.conn.execute("SELECT 1 FROM shopping_items WHERE id = ? AND user_id = ?", (existing, ctx.user_id)).fetchone():
            return _serialize(_row(ctx, existing)), False
        now = utc_now()
        cursor = ctx.conn.execute(
            "INSERT INTO shopping_items(name, quantity, unit, category, notes, created_at, updated_at, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (data.name, data.quantity, data.unit, data.category, data.notes, now, now, ctx.user_id),
        )
        foods.remember_key(ctx, idempotency_key, "shopping", cursor.lastrowid)
    return _serialize(_row(ctx, cursor.lastrowid)), True


def update_item(ctx, item_id, data):
    with transaction(ctx.conn):
        _row(ctx, item_id)
        ctx.conn.execute(
            "UPDATE shopping_items SET name = ?, quantity = ?, unit = ?, category = ?, notes = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (data.name, data.quantity, data.unit, data.category, data.notes, utc_now(), item_id, ctx.user_id),
        )
    return _serialize(_row(ctx, item_id))


def set_status(ctx, item_id, purchased):
    with transaction(ctx.conn):
        _row(ctx, item_id)
        now = utc_now()
        ctx.conn.execute(
            "UPDATE shopping_items SET purchased = ?, purchased_at = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (int(purchased), now if purchased else None, now, item_id, ctx.user_id),
        )
    return _serialize(_row(ctx, item_id))


def delete_item(ctx, item_id):
    with transaction(ctx.conn):
        item = _serialize(_row(ctx, item_id))
        ctx.conn.execute("DELETE FROM shopping_items WHERE id = ? AND user_id = ?", (item_id, ctx.user_id))
    return item


def clear_completed(ctx):
    with transaction(ctx.conn):
        removed = ctx.conn.execute("DELETE FROM shopping_items WHERE purchased = 1 AND user_id = ?", (ctx.user_id,)).rowcount
    return {"removed": removed}


def move_to_inventory(ctx, item_id, data):
    with transaction(ctx.conn):
        item = _row(ctx, item_id)
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
        food_id = foods.insert_food(ctx, food)
        now = utc_now()
        ctx.conn.execute(
            "UPDATE shopping_items SET purchased = 1, purchased_at = COALESCE(purchased_at, ?), inventory_food_id = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (now, food_id, now, item_id, ctx.user_id),
        )
    return {"shopping_item": _serialize(_row(ctx, item_id)), "food": foods.get_food(ctx, food_id)}
