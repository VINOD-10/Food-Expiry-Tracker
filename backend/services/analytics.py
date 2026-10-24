"""Analytics computed only from data that is actually stored."""
from collections import Counter
from datetime import datetime

from ..schemas import CATEGORIES
from . import foods


def _month_keys(today, count=6):
    year, month = today.year, today.month
    keys = []
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return keys[::-1]


def _local_month(timestamp, tz):
    try:
        return datetime.fromisoformat(timestamp).astimezone(tz).strftime("%Y-%m")
    except (TypeError, ValueError):
        return None


def analytics(conn, today, threshold, tz):
    items = foods._all(conn, today, threshold)
    months = _month_keys(today)
    status_counts = Counter(item["status"] for item in items)
    category_counts = Counter(item["category"] for item in items)
    additions = Counter(_local_month(item["created_at"], tz) for item in items)

    removals = conn.execute("SELECT reason, was_expired, removed_at FROM food_removals").fetchall()
    removal_months = {month: {"consumed": 0, "discarded": 0, "other": 0, "expired": 0} for month in months}
    for reason, was_expired, removed_at in removals:
        bucket = removal_months.get(_local_month(removed_at, tz))
        if bucket is not None:
            bucket[reason] += 1
            bucket["expired"] += was_expired
    reasons = Counter(row["reason"] for row in removals)
    tracked_since = conn.execute(
        "SELECT applied_at FROM schema_migrations WHERE name = 'alerts_removals_idempotency'"
    ).fetchone()

    return {
        "today": today.isoformat(),
        "threshold": threshold,
        "total": len(items),
        "status": {status: status_counts.get(status, 0) for status in ("safe", "soon", "today", "expired", "unknown")},
        "categories": sorted(
            ({"category": name, "count": category_counts[name]} for name in CATEGORIES if category_counts[name]),
            key=lambda entry: -entry["count"],
        ),
        "monthly_additions": [{"month": month, "count": additions.get(month, 0)} for month in months],
        "untracked_additions": additions.get(None, 0),
        "removals": {
            "total": len(removals),
            "consumed": reasons.get("consumed", 0),
            "discarded": reasons.get("discarded", 0),
            "other": reasons.get("other", 0),
            "expired_at_removal": sum(row["was_expired"] for row in removals),
            "monthly": [{"month": month, **removal_months[month]} for month in months],
            "tracked_since": tracked_since[0] if tracked_since else None,
        },
    }
