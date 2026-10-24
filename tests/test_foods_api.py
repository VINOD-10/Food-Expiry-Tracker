import sqlite3

import pytest

from .conftest import food, login, make_client, register


def test_create_list_get_update_delete(client):
    created = client.post("/api/foods", json=food(storage_location="Fridge", notes="  Opened  "))
    assert created.status_code == 201
    item = created.json()
    assert item["food_name"] == "Milk" and item["notes"] == "Opened"
    assert item["status"] == "safe" and item["days_remaining"] == 6
    assert item["created_at"]

    listing = client.get("/api/foods").json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == item["id"]
    assert client.get(f"/api/foods/{item['id']}").json()["food_name"] == "Milk"

    updated = client.put(f"/api/foods/{item['id']}", json=food(food_name="Toned milk", expiry_date="2026-10-25"))
    assert updated.status_code == 200
    assert updated.json()["food_name"] == "Toned milk" and updated.json()["status"] == "soon"
    assert client.get("/api/foods").json()["total"] == 1, "update must not duplicate"

    deleted = client.delete(f"/api/foods/{item['id']}", params={"reason": "consumed"})
    assert deleted.status_code == 200 and deleted.json()["deleted"]["id"] == item["id"]
    assert client.get(f"/api/foods/{item['id']}").status_code == 404
    assert client.get("/api/foods").json()["total"] == 0


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_ids_return_404(client, method):
    kwargs = {"json": food()} if method == "put" else {}
    response = getattr(client, method)("/api/foods/9999", **kwargs)
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Food item 9999 was not found"


def test_non_integer_id_is_rejected(client):
    assert client.get("/api/foods/abc").status_code == 422


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"food_name": ""}, "food_name"),
        ({"food_name": "   "}, "food_name"),
        ({"food_name": "x" * 101}, "food_name"),
        ({"expiry_date": "2026-02-30"}, "expiry_date"),
        ({"expiry_date": "30-10-2026"}, "expiry_date"),
        ({"expiry_date": ""}, "expiry_date"),
        ({"expiry_date": "1999-12-31"}, "_"),
        ({"quantity": 0}, "quantity"),
        ({"quantity": -2}, "quantity"),
        ({"quantity": "lots"}, "quantity"),
        ({"category": "Snacks"}, "category"),
        ({"unit": "tonnes"}, "unit"),
        ({"mfg_date": "2026-10-31", "expiry_date": "2026-10-30"}, "_"),
        ({"surprise": True}, "surprise"),
    ],
)
def test_invalid_input_is_rejected(client, overrides, field):
    response = client.post("/api/foods", json=food(**overrides))
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error" and field in body["fields"]
    assert client.get("/api/foods").json()["total"] == 0


def test_missing_required_fields(client):
    response = client.post("/api/foods", json={})
    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) >= {"food_name", "expiry_date"}


def test_manufacturing_date_in_future_rejected(client):
    response = client.post("/api/foods", json=food(mfg_date="2026-10-25"))
    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"mfg_date": "Manufacturing date cannot be in the future"}


def test_expired_food_can_still_be_recorded(client):
    response = client.post("/api/foods", json=food(expiry_date="2026-10-01", mfg_date="2026-09-01"))
    assert response.status_code == 201
    assert response.json()["status"] == "expired" and response.json()["days_remaining"] == -23


def test_quantity_without_unit_defaults_to_pieces(client):
    assert client.post("/api/foods", json=food(unit=None, quantity=3)).json()["unit"] == "pcs"


def test_idempotency_key_prevents_double_submission(client):
    headers = {"Idempotency-Key": "submit-abc-123"}
    first = client.post("/api/foods", json=food(), headers=headers)
    second = client.post("/api/foods", json=food(), headers=headers)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    assert client.get("/api/foods").json()["total"] == 1
    third = client.post("/api/foods", json=food(), headers={"Idempotency-Key": "submit-abc-456"})
    assert third.status_code == 201 and client.get("/api/foods").json()["total"] == 2


def test_bad_idempotency_key_rejected(client):
    assert client.post("/api/foods", json=food(), headers={"Idempotency-Key": "x"}).status_code == 422


def test_search_filter_sort_and_paginate(client):
    for name, category, expiry in [
        ("Apples", "Fruits", "2026-10-30"), ("Banana", "Fruits", "2026-10-25"),
        ("Cheddar", "Dairy", "2026-10-20"), ("100% juice", "Beverages", "2026-10-24"),
    ]:
        client.post("/api/foods", json=food(food_name=name, category=category, expiry_date=expiry))

    names = lambda **params: [item["food_name"] for item in client.get("/api/foods", params=params).json()["items"]]
    assert names(search="an") == ["Banana"]
    assert names(search="100%") == ["100% juice"]
    assert names(search="%") == ["100% juice"], "LIKE wildcards are escaped"
    assert names(category="Fruits", sort="name") == ["Apples", "Banana"]
    assert names(status="expired") == ["Cheddar"]
    assert names(status="today") == ["100% juice"]
    assert names(status="soon") == ["Banana"]
    assert names(status="safe") == ["Apples"]
    assert names(status="attention") == ["Cheddar", "100% juice", "Banana"]
    assert names(sort="expiry") == ["Cheddar", "100% juice", "Banana", "Apples"]
    assert names(sort="newest") == ["100% juice", "Cheddar", "Banana", "Apples"]

    page = client.get("/api/foods", params={"page_size": 3, "page": 2, "sort": "name"}).json()
    assert page["total"] == 4 and page["pages"] == 2 and [i["food_name"] for i in page["items"]] == ["Cheddar"]
    assert client.get("/api/foods", params={"page": 99, "page_size": 3}).json()["page"] == 2
    assert client.get("/api/foods", params={"status": "bogus"}).status_code == 422


def test_dashboard_counts_and_refresh_after_crud(client):
    for expiry in ["2026-10-20", "2026-10-24", "2026-10-26", "2026-11-30", "2026-12-30"]:
        client.post("/api/foods", json=food(expiry_date=expiry))
    counts = client.get("/api/dashboard").json()["counts"]
    assert counts == {"safe": 2, "soon": 1, "today": 1, "expired": 1, "unknown": 0, "total": 5, "expiring": 2}

    safe_id = client.get("/api/foods", params={"status": "safe"}).json()["items"][0]["id"]
    client.put(f"/api/foods/{safe_id}", json=food(expiry_date="2026-10-01"))
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["counts"]["expired"] == 2 and dashboard["counts"]["safe"] == 1
    assert dashboard["attention_total"] == 4 and dashboard["active_alerts"] == 4
    assert len(dashboard["recent"]) == 5

    client.delete(f"/api/foods/{safe_id}")
    assert client.get("/api/dashboard").json()["counts"]["total"] == 4


def test_alerts_dismiss_restore_and_reset_on_edit(client):
    soon = client.post("/api/foods", json=food(food_name="Yogurt", expiry_date="2026-10-26")).json()
    client.post("/api/foods", json=food(food_name="Rice", expiry_date="2027-01-01"))
    alerts = client.get("/api/alerts").json()
    assert [a["food_name"] for a in alerts["items"]] == ["Yogurt"] and alerts["counts"]["soon"] == 1

    assert client.post(f"/api/alerts/{soon['id']}/dismiss").json()["dismissed"] is True
    assert client.get("/api/alerts").json()["active"] == 0
    assert client.get("/api/alerts", params={"include_dismissed": True}).json()["items"][0]["dismissed"] is True

    # Editing the expiry date produces a new alert even though the old one was dismissed.
    client.put(f"/api/foods/{soon['id']}", json=food(food_name="Yogurt", expiry_date="2026-10-24"))
    alerts = client.get("/api/alerts").json()
    assert alerts["active"] == 1 and alerts["counts"]["today"] == 1

    client.post(f"/api/alerts/{soon['id']}/dismiss")
    client.delete(f"/api/alerts/{soon['id']}/dismiss")
    assert client.get("/api/alerts").json()["active"] == 1


def test_cannot_dismiss_safe_item(client):
    safe = client.post("/api/foods", json=food(expiry_date="2027-01-01")).json()
    response = client.post(f"/api/alerts/{safe['id']}/dismiss")
    assert response.status_code == 409


def test_deleting_food_cascades_dismissals(client, settings):
    item = client.post("/api/foods", json=food(expiry_date="2026-10-20")).json()
    client.post(f"/api/alerts/{item['id']}/dismiss")
    client.delete(f"/api/foods/{item['id']}", params={"reason": "discarded"})
    conn = sqlite3.connect(settings.database_path)
    assert conn.execute("SELECT count(*) FROM alert_dismissals").fetchone()[0] == 0
    assert conn.execute("SELECT reason, was_expired FROM food_removals").fetchall() == [("discarded", 1)]


def test_invalid_delete_reason(client):
    item = client.post("/api/foods", json=food()).json()
    assert client.delete(f"/api/foods/{item['id']}", params={"reason": "eaten-by-cat"}).status_code == 422
    assert client.get(f"/api/foods/{item['id']}").status_code == 200


def test_data_persists_after_restart(settings):
    with make_client(settings) as first:
        register(first)
        item_id = first.post("/api/foods", json=food(food_name="Paneer")).json()["id"]
    with make_client(settings) as second:
        login(second)
        assert second.get(f"/api/foods/{item_id}").json()["food_name"] == "Paneer"


def test_concurrent_requests_and_writes(client):
    from concurrent.futures import ThreadPoolExecutor

    def work(i):
        created = client.post("/api/foods", json=food(food_name=f"Item {i}"), headers={"Idempotency-Key": f"concurrent-{i:04d}"})
        return created.status_code, client.get("/api/dashboard").status_code, client.get("/api/alerts").status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(work, range(40)))
    assert all(result == (201, 200, 200) for result in results), results
    assert client.get("/api/foods").json()["total"] == 40


def test_empty_database_responses(client):
    assert client.get("/api/foods").json() == {"items": [], "total": 0, "page": 1, "page_size": 20, "pages": 1}
    dashboard = client.get("/api/dashboard").json()
    assert dashboard["counts"]["total"] == 0 and dashboard["recent"] == [] and dashboard["attention"] == []
    assert client.get("/api/alerts").json()["active"] == 0
