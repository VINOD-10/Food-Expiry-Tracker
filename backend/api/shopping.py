from typing import Literal

from fastapi import APIRouter, Depends, Response

from ..schemas import MoveToInventoryIn, ShoppingIn, ShoppingStatusIn
from ..services import shopping
from .deps import get_ctx, get_idempotency_key

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


@router.get("")
def list_items(status: Literal["all", "pending", "purchased"] = "all", ctx=Depends(get_ctx)):
    return shopping.list_items(ctx, status)


@router.post("", status_code=201)
def create_item(data: ShoppingIn, response: Response, idempotency_key=Depends(get_idempotency_key), ctx=Depends(get_ctx)):
    item, created = shopping.create_item(ctx, data, idempotency_key)
    if not created:
        response.status_code = 200
    return item


@router.post("/clear-completed")
def clear_completed(ctx=Depends(get_ctx)):
    return shopping.clear_completed(ctx)


@router.put("/{item_id}")
def update_item(item_id: int, data: ShoppingIn, ctx=Depends(get_ctx)):
    return shopping.update_item(ctx, item_id, data)


@router.patch("/{item_id}/status")
def set_status(item_id: int, data: ShoppingStatusIn, ctx=Depends(get_ctx)):
    return shopping.set_status(ctx, item_id, data.purchased)


@router.delete("/{item_id}")
def delete_item(item_id: int, ctx=Depends(get_ctx)):
    return {"deleted": shopping.delete_item(ctx, item_id)}


@router.post("/{item_id}/move-to-inventory", status_code=201)
def move_to_inventory(item_id: int, data: MoveToInventoryIn, ctx=Depends(get_ctx)):
    return shopping.move_to_inventory(ctx, item_id, data)
