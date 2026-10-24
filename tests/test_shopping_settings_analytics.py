import sqlite3

from .conftest import food, make_client


def test_shopping_crud_and_filters(client):
    eggs = client.post("/api/shopping", json={"name": " Eggs ", "quantity": 12, "unit": "pcs", "category": "Dairy"})
    assert eggs.status_code == 201 and eggs.json()["name"] == "Eggs" and eggs.json()["purchased"] is False
    bread = client.post("/api/shopping", json={"name": "Bread"}).json()

    edited = client.put(f"/api/shopping/{bread['id']}", json={"name": "Brown bread", "quantity": 1, "unit": "pack"})
    assert edited.json()["name"] == "Brown bread" and edited.json()["quantity"] == 1

    marked = client.patch(f"/api/shopping/{bread['id']}/status", json={"purchased": True}).json()
    assert marked["purchased"] is True and marked["purchased_at"]
    assert [i["name"] for i in client.get("/api/shopping", params={"status": "purchased"}).json()["items"]] == ["Brown bread"]
    assert [i["name"] for i in client.get("/api/shopping", params={"status": "pending"}).json()["items"]] == ["Eggs"]
    assert client.get("/api/shopping").json()["counts"] == {"pending": 1, "purchased": 1, "all": 2}

    unmarked = client.patch(f"/api/shopping/{bread['id']}/status", json={"purchased": False}).json()
    assert unmarked["purchased"] is False and unmarked["purchased_at"] is None

    assert client.delete(f"/api/shopping/{eggs.json()['id']}").status_code == 200
    assert client.get("/api/shopping").json()["counts"]["all"] == 1


def test_shopping_validation_and_missing(client):
    assert client.post("/api/shopping", json={"name": ""}).status_code == 422
    assert client.post("/api/shopping", json={"name": "Oil", "quantity": 0}).status_code == 422
    assert client.put("/api/shopping/999", json={"name": "Oil"}).status_code == 404
    assert client.patch("/api/shopping/999/status", json={"purchased": True}).status_code == 404
    assert client.delete("/api/shopping/999").status_code == 404


def test_shopping_idempotency(client):
    headers = {"Idempotency-Key": "shopping-key-1"}
    client.post("/api/shopping", json={"name": "Salt"}, headers=headers)
    client.post("/api/shopping", json={"name": "Salt"}, headers=headers)
    assert client.get("/api/shopping").json()["counts"]["all"] == 1


def test_clear_completed(client):
    for name in ("A", "B", "C"):
        client.post("/api/shopping", json={"name": name})
    items = client.get("/api/shopping").json()["items"]
    for item in items[:2]:
        client.patch(f"/api/shopping/{item['id']}/status", json={"purchased": True})
    assert client.post("/api/shopping/clear-completed").json() == {"removed": 2}
    assert [i["name"] for i in client.get("/api/shopping").json()["items"]] == ["A"]


def test_move_to_inventory(client, settings):
    item = client.post("/api/shopping", json={"name": "Curd", "quantity": 2, "unit": "pack", "category": "Dairy"}).json()
    assert client.post(f"/api/shopping/{item['id']}/move-to-inventory", json={}).status_code == 422, "expiry date is required"
    bad = client.post(f"/api/shopping/{item['id']}/move-to-inventory", json={"expiry_date": "2026-10-20", "mfg_date": "2026-10-22"})
    assert bad.status_code == 422

    moved = client.post(f"/api/shopping/{item['id']}/move-to-inventory", json={"expiry_date": "2026-10-27", "storage_location": "Fridge"})
    assert moved.status_code == 201
    body = moved.json()
    assert body["food"]["food_name"] == "Curd" and body["food"]["category"] == "Dairy" and body["food"]["quantity"] == 2
    assert body["food"]["status"] == "soon"
    assert body["shopping_item"]["purchased"] is True and body["shopping_item"]["inventory_food_id"] == body["food"]["id"]

    again = client.post(f"/api/shopping/{item['id']}/move-to-inventory", json={"expiry_date": "2026-10-27"})
    assert again.status_code == 409
    assert client.get("/api/foods").json()["total"] == 1

    # Deleting the inventory item clears the link through the foreign key.
    client.delete(f"/api/foods/{body['food']['id']}")
    conn = sqlite3.connect(settings.database_path)
    assert conn.execute("SELECT inventory_food_id FROM shopping_items").fetchone() == (None,)


def test_settings_persist_and_change_status(client, settings):
    defaults = client.get("/api/settings").json()
    assert defaults == {"expiry_threshold": 3, "date_format": "%d-%m-%Y", "default_sort": "Expiry date", "theme": "system", "browser_notifications": False}

    client.post("/api/foods", json=food(expiry_date="2026-10-29"))
    assert client.get("/api/foods").json()["items"][0]["status"] == "safe"

    saved = client.put("/api/settings", json={**defaults, "expiry_threshold": 7, "theme": "dark", "date_format": "%Y-%m-%d"})
    assert saved.status_code == 200 and saved.json()["expiry_threshold"] == 7
    assert client.get("/api/foods").json()["items"][0]["status"] == "soon"

    with make_client(settings) as restarted:
        assert restarted.get("/api/settings").json()["theme"] == "dark"


def test_settings_validation(client):
    defaults = client.get("/api/settings").json()
    assert client.put("/api/settings", json={**defaults, "expiry_threshold": 31}).status_code == 422
    assert client.put("/api/settings", json={**defaults, "expiry_threshold": -1}).status_code == 422
    assert client.put("/api/settings", json={**defaults, "date_format": "%s"}).status_code == 422
    assert client.put("/api/settings", json={**defaults, "theme": "neon"}).status_code == 422
    assert client.get("/api/settings").json() == defaults


def test_analytics_uses_stored_data_only(client, settings):
    client.post("/api/foods", json=food(category="Fruits", expiry_date="2026-10-20"))
    client.post("/api/foods", json=food(category="Fruits", expiry_date="2026-11-20"))
    third = client.post("/api/foods", json=food(category="Dairy", expiry_date="2026-10-21")).json()
    client.delete(f"/api/foods/{third['id']}", params={"reason": "discarded"})
    # A row from the desktop app that predates created_at tracking.
    conn = sqlite3.connect(settings.database_path)
    conn.execute("INSERT INTO food(food_name, mfg_date, expiry_date, purchased_at, expires_at) VALUES ('Old', 'x', 'y', 'x', 'y')")
    conn.execute("UPDATE food SET created_at = NULL WHERE food_name = 'Old'")
    conn.commit()

    data = client.get("/api/analytics").json()
    assert data["total"] == 3
    assert data["status"] == {"safe": 1, "soon": 0, "today": 0, "expired": 1, "unknown": 1}
    assert data["categories"][0] == {"category": "Fruits", "count": 2}
    assert data["untracked_additions"] == 1
    assert data["monthly_additions"][-1]["month"] == "2026-10"
    assert data["removals"]["discarded"] == 1 and data["removals"]["expired_at_removal"] == 1
    assert data["removals"]["tracked_since"]


def test_meta_health_and_unknown_routes(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert "Dairy" in meta["categories"] and meta["timezone"] == "Asia/Kolkata"
    assert client.get("/api/does-not-exist").status_code == 404


def test_security_headers_and_cors(client):
    response = client.get("/api/health")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    allowed = client.options("/api/foods", headers={"Origin": "http://127.0.0.1:8000", "Access-Control-Request-Method": "POST"})
    assert allowed.headers.get("access-control-allow-origin") == "http://127.0.0.1:8000"
    blocked = client.options("/api/foods", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in blocked.headers


def test_server_errors_do_not_leak_details(client, monkeypatch):
    from backend.services import foods as food_service

    def boom(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk I/O error at /secret/path")

    monkeypatch.setattr(food_service, "dashboard", boom)
    response = client.get("/api/dashboard")
    assert response.status_code == 500
    assert "secret" not in response.text and response.json()["error"]["code"] == "database_error"


def test_frontend_is_served(client):
    response = client.get("/")
    assert response.status_code == 200 and "Food Expiry Tracker" in response.text
