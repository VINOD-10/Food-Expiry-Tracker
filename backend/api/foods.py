from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from ..schemas import CATEGORIES, FoodIn, RemovalReason
from ..services import foods
from .deps import get_ctx, get_idempotency_key

router = APIRouter(prefix="/api", tags=["inventory"])
StatusFilter = Literal["expired", "today", "soon", "safe", "unknown", "attention"]


@router.get("/foods")
def list_foods(
    search: str | None = Query(default=None, max_length=100),
    category: Literal[CATEGORIES] | None = None,
    status: StatusFilter | None = None,
    sort: Literal["expiry", "newest", "name"] = "expiry",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    ctx=Depends(get_ctx),
):
    search = search.strip() if search else None
    return foods.list_foods(ctx, search, category, status, sort, page, page_size)


@router.post("/foods", status_code=201)
def create_food(data: FoodIn, response: Response, idempotency_key=Depends(get_idempotency_key), ctx=Depends(get_ctx)):
    item, created = foods.create_food(ctx, data, idempotency_key)
    if not created:
        response.status_code = 200
    return item


@router.get("/foods/{food_id}")
def get_food(food_id: int, ctx=Depends(get_ctx)):
    return foods.get_food(ctx, food_id)


@router.put("/foods/{food_id}")
def update_food(food_id: int, data: FoodIn, ctx=Depends(get_ctx)):
    return foods.update_food(ctx, food_id, data)


@router.delete("/foods/{food_id}")
def delete_food(food_id: int, reason: RemovalReason = "other", ctx=Depends(get_ctx)):
    return {"deleted": foods.delete_food(ctx, food_id, reason)}


@router.get("/dashboard", tags=["dashboard"])
def dashboard(ctx=Depends(get_ctx)):
    return foods.dashboard(ctx)


@router.get("/alerts", tags=["alerts"])
def alerts(include_dismissed: bool = False, ctx=Depends(get_ctx)):
    return foods.list_alerts(ctx, include_dismissed)


@router.post("/alerts/{food_id}/dismiss", tags=["alerts"])
def dismiss_alert(food_id: int, ctx=Depends(get_ctx)):
    return foods.dismiss_alert(ctx, food_id)


@router.delete("/alerts/{food_id}/dismiss", tags=["alerts"])
def restore_alert(food_id: int, ctx=Depends(get_ctx)):
    return foods.restore_alert(ctx, food_id)
