"""FastAPI entry point: `uvicorn backend.main:app` from the project root."""
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import foods, misc, shopping
from .config import load_settings
from .db import connect
from .errors import AppError
from .migrations import migrate

logger = logging.getLogger("food_tracker")
FIELD_LABELS = {
    "food_name": "Food name", "name": "Item name", "category": "Category", "quantity": "Quantity",
    "unit": "Unit", "mfg_date": "Manufacturing date", "expiry_date": "Expiry date",
    "storage_location": "Storage location", "notes": "Notes", "expiry_threshold": "Alert threshold",
}
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


def _error(status, code, message, fields=None):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "fields": fields or {}}})


def create_app(settings=None):
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app):
        conn = connect(settings.database_path)
        try:
            backup = migrate(conn, settings.backup_dir)
            if backup:
                logger.warning("Database backed up to %s before migrating", backup)
        finally:
            conn.close()
        yield

    app = FastAPI(title="Food Expiry Tracker API", version="2.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AppError)
    async def app_error(_request, error: AppError):
        fields = {error.field: error.message} if error.field else {}
        return _error(error.status_code, error.code, error.message, fields)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, error: RequestValidationError):
        fields, messages = {}, []
        for issue in error.errors():
            loc = [str(part) for part in issue["loc"] if part not in ("body", "query", "path", "header")]
            field = loc[-1] if loc else None
            message = issue["msg"].removeprefix("Value error, ")
            kind, ctx = issue["type"], issue.get("ctx") or {}
            if kind == "missing" or (kind == "string_too_short" and ctx.get("min_length") == 1):
                message = "This field is required"
            elif kind == "string_too_long":
                message = f"Must be {ctx.get('max_length')} characters or fewer"
            elif kind == "greater_than":
                message = f"Must be greater than {ctx.get('gt')}"
            elif kind == "greater_than_equal":
                message = f"Must be at least {ctx.get('ge')}"
            elif kind == "less_than_equal":
                message = f"Must be {ctx.get('le')} or less"
            elif kind.startswith("date_") or kind == "date_type":
                message = "Enter a valid calendar date (YYYY-MM-DD)"
            elif kind in ("float_parsing", "float_type", "int_parsing", "int_type"):
                message = "Enter a valid number"
            elif kind == "literal_error":
                message = "Choose one of the listed options"
            elif kind == "json_invalid":
                message = "The request body is not valid JSON"
            elif kind == "extra_forbidden":
                message = "Unknown field"
            label = FIELD_LABELS.get(field, field)
            fields.setdefault(field or "_", message)
            messages.append(f"{label}: {message}" if label else message)
        return _error(422, "validation_error", messages[0] if messages else "Invalid request", fields)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request, error: StarletteHTTPException):
        message = "Resource not found" if error.status_code == 404 else str(error.detail)
        return _error(error.status_code, "http_error", message)

    @app.exception_handler(sqlite3.Error)
    async def database_error(_request, error: sqlite3.Error):
        logger.exception("Database error", exc_info=error)
        return _error(500, "database_error", "The database could not complete this request. Please try again.")

    @app.exception_handler(Exception)
    async def unexpected_error(_request, error: Exception):
        logger.exception("Unexpected error", exc_info=error)
        return _error(500, "server_error", "Something went wrong on the server. Please try again.")

    app.include_router(foods.router)
    app.include_router(shopping.router)
    app.include_router(misc.router)

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    async def unknown_api(path: str):
        return _error(404, "not_found", f"Unknown API endpoint: /api/{path}")

    if settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
