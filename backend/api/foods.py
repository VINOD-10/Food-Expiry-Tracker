from typing import Literal

from fastapi import APIRouter, Depends, Query, Response

from ..schemas import CATEGORIES, FoodIn, RemovalReason
from ..services import foods
from .deps import get_conn, get_idempotency_key, get_threshold, get_today

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
    conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold),
):
    search = search.strip() if search else None
    return foods.list_foods(conn, today, threshold, search, category, status, sort, page, page_size)


@router.post("/foods", status_code=201)
def create_food(
    data: FoodIn, response: Response, idempotency_key=Depends(get_idempotency_key),
    conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold),
):
    item, created = foods.create_food(conn, data, today, threshold, idempotency_key)
    if not created:
        response.status_code = 200
    return item


@router.get("/foods/{food_id}")
def get_food(food_id: int, conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return foods.get_food(conn, food_id, today, threshold)


@router.put("/foods/{food_id}")
def update_food(food_id: int, data: FoodIn, conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return foods.update_food(conn, food_id, data, today, threshold)


@router.delete("/foods/{food_id}")
def delete_food(
    food_id: int, reason: RemovalReason = "other",
    conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold),
):
    return {"deleted": foods.delete_food(conn, food_id, reason, today, threshold)}


@router.get("/dashboard", tags=["dashboard"])
def dashboard(conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return foods.dashboard(conn, today, threshold)


@router.get("/alerts", tags=["alerts"])
def alerts(include_dismissed: bool = False, conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return foods.list_alerts(conn, today, threshold, include_dismissed)


@router.post("/alerts/{food_id}/dismiss", tags=["alerts"])
def dismiss_alert(food_id: int, conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return foods.dismiss_alert(conn, food_id, today, threshold)


@router.delete("/alerts/{food_id}/dismiss", tags=["alerts"])
def restore_alert(food_id: int, conn=Depends(get_conn), today=Depends(get_today), threshold=Depends(get_threshold)):
    return foods.restore_alert(conn, food_id, today, threshold)
