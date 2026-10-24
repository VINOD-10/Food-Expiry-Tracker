from typing import Literal

from fastapi import APIRouter, Depends, Response

from ..schemas import MoveToInventoryIn, ShoppingIn, ShoppingStatusIn
from ..services import shopping
from .deps import get_conn, get_idempotency_key, get_threshold, get_today

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


@router.get("")
def list_items(status: Literal["all", "pending", "purchased"] = "all", conn=Depends(get_conn)):
    return shopping.list_items(conn, status)


@router.post("", status_code=201)
def create_item(data: ShoppingIn, response: Response, idempotency_key=Depends(get_idempotency_key), conn=Depends(get_conn)):
    item, created = shopping.create_item(conn, data, idempotency_key)
    if not created:
        response.status_code = 200
    return item


@router.post("/clear-completed")
def clear_completed(conn=Depends(get_conn)):
    return shopping.clear_completed(conn)


@router.put("/{item_id}")
def update_item(item_id: int, data: ShoppingIn, conn=Depends(get_conn)):
    return shopping.update_item(conn, item_id, data)


@router.patch("/{item_id}/status")
def set_status(item_id: int, data: ShoppingStatusIn, conn=Depends(get_conn)):
    return shopping.set_status(conn, item_id, data.purchased)


@router.delete("/{item_id}")
def delete_item(item_id: int, conn=Depends(get_conn)):
    return {"deleted": shopping.delete_item(conn, item_id)}


@router.post("/{item_id}/move-to-inventory", status_code=201)
def move_to_inventory(item_id: int, data: MoveToInventoryIn, conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return shopping.move_to_inventory(conn, item_id, data, today, threshold)
