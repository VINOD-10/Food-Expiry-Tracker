"""The desktop app (app.py) and the web API must agree, and share removal history."""
import gc
import sqlite3
from datetime import timedelta

import pytest

import database
from .conftest import TODAY, food


@pytest.fixture
def desktop_db(settings, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", settings.database_path)
    return settings.database_path


def test_desktop_delete_records_reason(client, desktop_db):
    item = client.post("/api/foods", json=food(food_name="Curd", category="Dairy", expiry_date="2026-10-20")).json()
    database.delete(item["id"], "discarded", True)
    rows = sqlite3.connect(desktop_db).execute("SELECT food_name, category, expiry_date, reason, was_expired FROM food_removals").fetchall()
    assert rows == [("Curd", "Dairy", "2026-10-20", "discarded", 1)]
    assert client.get("/api/analytics").json()["removals"]["discarded"] == 1


def test_desktop_delete_without_reason_keeps_old_behaviour(client, desktop_db):
    item = client.post("/api/foods", json=food()).json()
    database.delete(item["id"])
    conn = sqlite3.connect(desktop_db)
    assert conn.execute("SELECT count(*) FROM food").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM food_removals").fetchone()[0] == 0


def test_desktop_delete_on_database_never_opened_by_web_app(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "legacy.db")
    database.connect()
    database.insert("Bread", "2026-10-20T12:00:00", "2026-10-25T23:59:00")
    food_id = database.fetch()[0][0]
    database.delete(food_id, "consumed", False)
    assert database.fetch() == []


def test_desktop_sees_only_the_owners_data(client, desktop_db, settings):
    from .conftest import make_client, register

    client.post("/api/foods", json=food(food_name="Owner bread"))
    with make_client(settings) as other:
        register(other, "flatmate@example.com", "Flatmate")
        flatmate_item = other.post("/api/foods", json=food(food_name="Flatmate cheese")).json()
        assert [row[1] for row in database.fetch()] == ["Owner bread"]
        assert database.search("cheese") == []
        # Desktop edits and deletes cannot reach another user's rows.
        database.update(flatmate_item["id"], "changed", "2026-10-01T12:00:00", "2026-10-30T23:59:00")
        database.delete(flatmate_item["id"], "consumed")
        database.delete_all()
        assert other.get(f"/api/foods/{flatmate_item['id']}").json()["food_name"] == "Flatmate cheese"
    assert client.get("/api/foods").json()["total"] == 0, "delete_all only cleared the owner's items"


def test_desktop_inserts_and_settings_belong_to_owner(client, desktop_db):
    database.insert("Desktop dal", "2026-10-20T12:00:00", "2026-11-20T23:59:00")
    assert [i["food_name"] for i in client.get("/api/foods").json()["items"]] == ["Desktop dal"]
    client.put("/api/settings", json={**client.get("/api/settings").json(), "expiry_threshold": 9})
    assert database.get_settings()["expiry_threshold"] == "9"


def test_desktop_and_web_agree_on_status(client, desktop_db, monkeypatch):
    tk = pytest.importorskip("tkinter")
    import app

    monkeypatch.setattr(app, "today_in", lambda _tz: TODAY)
    # The refresh loop starts a background thread; a Tk object released from that
    # thread can abort the interpreter, so the test never starts it.
    monkeypatch.setattr(app.FoodExpiryApp, "_schedule_refresh", lambda self: None)
    for offset in (-1, 0, 1, 3, 4):
        client.post("/api/foods", json=food(food_name=f"d{offset}", expiry_date=(TODAY + timedelta(days=offset)).isoformat()))
    web = {item["id"]: (item["status_label"], item["days_remaining"]) for item in client.get("/api/foods").json()["items"]}
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available for Tk")
    try:
        root.withdraw()
        ui = app.FoodExpiryApp(root)
        desktop = {row[0]: (ui._row_details(row)["status"], ui._row_details(row)["days_remaining"]) for row in database.fetch()}
        assert desktop == web
        assert ui._counts() == {"total": 5, "fresh": 1, "soon": 3, "expired": 1}
    finally:
        root.destroy()
        # Tk objects must be freed on the thread that created them. Without this, a later
        # garbage collection inside a web-server worker thread frees them and Tcl aborts.
        del root
        ui = None
        gc.collect()
