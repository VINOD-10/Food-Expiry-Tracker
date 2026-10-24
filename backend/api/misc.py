from fastapi import APIRouter, Depends, Request

from ..expiry_engine import STATUS_LABELS
from ..schemas import CATEGORIES, DATE_FORMATS, SORTS, STORAGE_LOCATIONS, THEMES, UNITS, SettingsIn
from ..services import analytics as analytics_service
from ..services import settings as settings_service
from .deps import get_conn, get_ctx, get_current_user, get_today

router = APIRouter(prefix="/api")


@router.get("/health", tags=["system"])
def health(conn=Depends(get_conn)):
    conn.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@router.get("/meta", tags=["system"])
def meta(request: Request, today=Depends(get_today)):
    return {
        "categories": CATEGORIES,
        "units": UNITS,
        "storage_locations": STORAGE_LOCATIONS,
        "date_formats": DATE_FORMATS,
        "sorts": SORTS,
        "themes": THEMES,
        "status_labels": STATUS_LABELS,
        "timezone": request.app.state.settings.timezone_name,
        "today": today.isoformat(),
        "allow_signup": request.app.state.settings.allow_signup,
    }


@router.get("/settings", tags=["settings"])
def read_settings(user=Depends(get_current_user), conn=Depends(get_conn)):
    return settings_service.get_settings(conn, user["id"])


@router.put("/settings", tags=["settings"])
def update_settings(data: SettingsIn, user=Depends(get_current_user), conn=Depends(get_conn)):
    return settings_service.save_settings(conn, user["id"], data)


@router.get("/analytics", tags=["analytics"])
def analytics(request: Request, ctx=Depends(get_ctx)):
    return analytics_service.analytics(ctx, request.app.state.settings.timezone)
