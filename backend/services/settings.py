"""Per-user settings stored in the user_settings table."""
from ..schemas import DATE_FORMATS, SORTS, THEMES

DEFAULTS = {
    "expiry_threshold": 3,
    "date_format": "%d-%m-%Y",
    "default_sort": "Expiry date",
    "theme": "system",
    "browser_notifications": False,
}


def get_settings(conn, user_id):
    stored = dict(conn.execute(
        "SELECT setting_key, setting_value FROM user_settings WHERE user_id = ?", (user_id,)
    ).fetchall())
    result = dict(DEFAULTS)
    try:
        result["expiry_threshold"] = min(30, max(0, int(stored.get("expiry_threshold", 3))))
    except ValueError:
        pass
    for key, allowed in (("date_format", DATE_FORMATS), ("default_sort", SORTS), ("theme", THEMES)):
        if stored.get(key) in allowed:
            result[key] = stored[key]
    result["browser_notifications"] = stored.get("browser_notifications") == "true"
    return result


def save_settings(conn, user_id, values):
    rows = {
        "expiry_threshold": str(values.expiry_threshold),
        "date_format": values.date_format,
        "default_sort": values.default_sort,
        "theme": values.theme,
        "browser_notifications": "true" if values.browser_notifications else "false",
    }
    conn.executemany(
        "INSERT INTO user_settings(user_id, setting_key, setting_value) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value",
        [(user_id, key, value) for key, value in rows.items()],
    )
    return get_settings(conn, user_id)


def threshold(conn, user_id):
    return get_settings(conn, user_id)["expiry_threshold"]
