"""The single place where expiry status is decided.

Status is calendar-date based in the application timezone, so an item that
expires "today" stays "Expires today" until local midnight regardless of the
time stored alongside the date by the desktop app.
"""
from datetime import date, datetime

from expiry import parse_datetime

STATUS_LABELS = {
    "expired": "Expired",
    "today": "Expires today",
    "soon": "Expiring soon",
    "safe": "Safe",
    "unknown": "Unknown date",
}
ALERT_STATUSES = ("expired", "today", "soon")


def today_in(tz):
    return datetime.now(tz).date()


def parse_stored_date(value):
    """Return the calendar date of a stored value, or None when unreadable."""
    if not value:
        return None
    try:
        return parse_datetime(value).date()
    except ValueError:
        return None


def evaluate(expiry: date | None, today: date, threshold: int):
    if expiry is None:
        return {"status": "unknown", "status_label": STATUS_LABELS["unknown"], "days_remaining": None}
    days = (expiry - today).days
    if days < 0:
        status = "expired"
    elif days == 0:
        status = "today"
    elif days <= threshold:
        status = "soon"
    else:
        status = "safe"
    return {"status": status, "status_label": STATUS_LABELS[status], "days_remaining": days}
