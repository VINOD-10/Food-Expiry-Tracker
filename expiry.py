from datetime import datetime, timedelta


STORAGE_FORMAT = "%Y-%m-%dT%H:%M:%S"
DISPLAY_FORMAT = "%d %b %Y, %I:%M %p"
LEGACY_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y")


def parse_datetime(value, default_time=(12, 0)):
    """Parse stored ISO values and legacy date-only values into local datetimes."""
    if isinstance(value, datetime):
        return value
    if not value:
        raise ValueError("A date is required")
    text = str(value).strip()
    for date_format in (STORAGE_FORMAT, "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            continue
    for date_format in LEGACY_FORMATS:
        try:
            return datetime.strptime(text, date_format).replace(hour=default_time[0], minute=default_time[1])
        except ValueError:
            continue
    raise ValueError(f"Unsupported date: {value}")


def to_storage(value):
    return parse_datetime(value).strftime(STORAGE_FORMAT)


def get_expiry_alert_threshold(total_duration):
    """Return a proportional warning window, anchored at 12h, 2d, and 5d."""
    total_seconds = max(0.0, total_duration.total_seconds())
    day = 24 * 60 * 60
    anchors = ((day, 12 * 60 * 60), (7 * day, 2 * day), (31 * day, 5 * day))
    if total_seconds <= anchors[0][0]:
        warning_seconds = total_seconds / 2
    elif total_seconds <= anchors[1][0]:
        warning_seconds = _interpolate(total_seconds, anchors[0], anchors[1])
    elif total_seconds <= anchors[2][0]:
        warning_seconds = _interpolate(total_seconds, anchors[1], anchors[2])
    else:
        warning_seconds = 5 * day
    return timedelta(seconds=min(total_seconds, warning_seconds))


def _interpolate(value, start, end):
    start_value, start_warning = start
    end_value, end_warning = end
    fraction = (value - start_value) / (end_value - start_value)
    return start_warning + fraction * (end_warning - start_warning)


def get_expiry_details(purchased_at, expires_at, now=None):
    purchased = parse_datetime(purchased_at)
    expires = parse_datetime(expires_at)
    current = now or datetime.now()
    total_duration = expires - purchased
    remaining = expires - current
    threshold = get_expiry_alert_threshold(total_duration)
    if remaining.total_seconds() <= 0:
        status, alert_level = "Expired", "expired"
    elif remaining <= threshold / 2:
        status, alert_level = "Expiring Soon", "urgent"
    elif remaining <= threshold:
        status, alert_level = "Expiring Soon", "soon"
    else:
        status, alert_level = "Fresh", "fresh"
    return {
        "purchased_at": purchased,
        "expires_at": expires,
        "total_duration": total_duration,
        "remaining": remaining,
        "threshold": threshold,
        "status": status,
        "alert_level": alert_level,
    }


def format_remaining(remaining):
    seconds = remaining.total_seconds()
    if seconds <= 0:
        elapsed = timedelta(seconds=abs(seconds))
        return f"Expired {format_duration(elapsed)} ago"
    return f"{format_duration(remaining)} remaining"


def format_duration(duration):
    total_minutes = max(1, int(duration.total_seconds() // 60))
    days, remainder = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} day" + ("s" if days != 1 else ""))
    if hours and len(parts) < 2:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if minutes and not parts:
        parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
    return " ".join(parts[:2])


def format_datetime(value):
    return parse_datetime(value).strftime(DISPLAY_FORMAT)
