from datetime import date

import pytest

from backend.expiry_engine import evaluate, parse_stored_date

TODAY = date(2026, 10, 24)


@pytest.mark.parametrize(
    ("expiry", "status", "days"),
    [
        (date(2026, 10, 23), "expired", -1),
        (date(2026, 10, 24), "today", 0),
        (date(2026, 10, 25), "soon", 1),
        (date(2026, 10, 27), "soon", 3),
        (date(2026, 10, 28), "safe", 4),
        (date(2025, 10, 24), "expired", -365),
    ],
)
def test_status_boundaries(expiry, status, days):
    result = evaluate(expiry, TODAY, 3)
    assert (result["status"], result["days_remaining"]) == (status, days)


def test_threshold_zero_has_no_soon_window():
    assert evaluate(date(2026, 10, 25), TODAY, 0)["status"] == "safe"
    assert evaluate(TODAY, TODAY, 0)["status"] == "today"


def test_month_year_and_leap_boundaries():
    assert evaluate(date(2026, 2, 1), date(2026, 1, 31), 3)["days_remaining"] == 1
    assert evaluate(date(2027, 1, 1), date(2026, 12, 31), 3)["days_remaining"] == 1
    assert evaluate(date(2028, 2, 29), date(2028, 2, 28), 3)["days_remaining"] == 1
    assert evaluate(date(2028, 3, 1), date(2028, 2, 28), 3)["days_remaining"] == 2
    assert evaluate(date(2027, 3, 1), date(2027, 2, 28), 3)["days_remaining"] == 1


def test_labels_and_unknown():
    assert evaluate(TODAY, TODAY, 3)["status_label"] == "Expires today"
    assert evaluate(None, TODAY, 3) == {"status": "unknown", "status_label": "Unknown date", "days_remaining": None}


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ("2026-09-10T23:59:00", date(2026, 9, 10)),
        ("10-09-2026", date(2026, 9, 10)),
        ("2026-09-10", date(2026, 9, 10)),
        ("not a date", None),
        (None, None),
    ],
)
def test_parse_stored_dates_from_desktop_app(stored, expected):
    assert parse_stored_date(stored) == expected
