import sqlite3
from dataclasses import replace

import pytest

from backend.services.auth import verify_password
from .conftest import PASSWORD, food, login, make_client, register

PROTECTED = [
    ("get", "/api/foods"), ("post", "/api/foods"), ("get", "/api/foods/1"), ("put", "/api/foods/1"),
    ("delete", "/api/foods/1"), ("get", "/api/dashboard"), ("get", "/api/alerts"), ("post", "/api/alerts/1/dismiss"),
    ("get", "/api/shopping"), ("post", "/api/shopping"), ("post", "/api/shopping/clear-completed"),
    ("get", "/api/analytics"), ("get", "/api/settings"), ("put", "/api/settings"), ("get", "/api/auth/me"),
    ("put", "/api/auth/password"),
]


@pytest.fixture
def anon(settings):
    with make_client(settings) as test_client:
        yield test_client


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_every_data_endpoint_requires_login(anon, method, path):
    response = getattr(anon, method)(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_public_endpoints_stay_open(anon):
    assert anon.get("/api/health").status_code == 200
    assert anon.get("/api/meta").json()["allow_signup"] is True
    assert anon.get("/").status_code == 200


def test_register_login_logout_cycle(anon, settings):
    user = register(anon, "Asha@Example.com", "Asha")
    assert user == {**user, "email": "asha@example.com", "display_name": "Asha", "is_owner": True}
    assert anon.get("/api/auth/me").json()["email"] == "asha@example.com"

    assert anon.post("/api/auth/logout").status_code == 200
    assert anon.get("/api/foods").status_code == 401

    assert login(anon, "ASHA@example.com ").status_code == 200, "email is case- and space-insensitive"
    assert anon.get("/api/foods").status_code == 200

    stored = sqlite3.connect(settings.database_path).execute("SELECT password_hash FROM users").fetchone()[0]
    assert PASSWORD not in stored and stored.startswith("scrypt$") and verify_password(PASSWORD, stored)


def test_session_cookie_is_httponly_and_samesite(anon):
    response = anon.post("/api/auth/register", json={"display_name": "A", "email": "a@example.com", "password": PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "fet_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "max-age=604800" in cookie


def test_remember_me_extends_session(anon):
    register(anon)
    response = anon.post("/api/auth/login", json={"email": "owner@example.com", "password": PASSWORD, "remember": True})
    assert "max-age=2592000" in response.headers["set-cookie"].lower()


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"display_name": "", "email": "a@example.com", "password": PASSWORD}, "display_name"),
        ({"display_name": "A", "email": "not-an-email", "password": PASSWORD}, "email"),
        ({"display_name": "A", "email": "a@example.com", "password": "short"}, "password"),
        ({"display_name": "A", "email": "a@example.com", "password": "        "}, "password"),
        ({"display_name": "A", "email": "a@example.com", "password": "x" * 129}, "password"),
    ],
)
def test_registration_validation(anon, payload, field):
    response = anon.post("/api/auth/register", json=payload)
    assert response.status_code == 422 and field in response.json()["error"]["fields"]


def test_duplicate_email_rejected(anon, settings):
    register(anon)
    with make_client(settings) as other:
        response = other.post("/api/auth/register", json={"display_name": "B", "email": "OWNER@example.com", "password": PASSWORD})
    assert response.status_code == 409 and "email" in response.json()["error"]["fields"]


def test_wrong_password_and_unknown_email_get_same_message(anon):
    register(anon)
    anon.post("/api/auth/logout")
    wrong = login(anon, password="wrong password")
    unknown = login(anon, email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"] == "Incorrect email or password"


def test_repeated_failures_are_throttled(anon):
    register(anon)
    for _ in range(5):
        assert login(anon, password="nope nope nope").status_code == 401
    blocked = login(anon)  # even the right password is refused while throttled
    assert blocked.status_code == 429 and "15 minutes" in blocked.json()["error"]["message"]


def test_successful_login_clears_failures(anon):
    register(anon)
    for _ in range(4):
        login(anon, password="nope nope nope")
    assert login(anon).status_code == 200
    for _ in range(4):
        login(anon, password="nope nope nope")
    assert login(anon).status_code == 200


def test_expired_session_is_rejected(client, settings):
    sqlite3.connect(settings.database_path, isolation_level=None).execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00Z'")
    assert client.get("/api/foods").status_code == 401


def test_change_password_signs_out_other_devices(client, settings):
    with make_client(settings) as phone:
        assert login(phone).status_code == 200
        bad = client.put("/api/auth/password", json={"current_password": "wrong", "new_password": "a new password"})
        assert bad.status_code == 422 and "current_password" in bad.json()["error"]["fields"]
        assert client.put("/api/auth/password", json={"current_password": PASSWORD, "new_password": "short"}).status_code == 422

        assert client.put("/api/auth/password", json={"current_password": PASSWORD, "new_password": "a new password"}).status_code == 200
        assert client.get("/api/foods").status_code == 200, "the device that changed it stays signed in"
        assert phone.get("/api/foods").status_code == 401, "other devices are signed out"
        assert login(phone).status_code == 401
        assert login(phone, password="a new password").status_code == 200


def test_signup_can_be_closed_after_owner_exists(tmp_path):
    from backend.config import load_settings
    closed = replace(load_settings(), database_path=tmp_path / "food.db", backup_dir=tmp_path / "b", allow_signup=False)
    with make_client(closed) as first:
        register(first)  # the owner can always be created
    with make_client(closed) as second:
        response = second.post("/api/auth/register", json={"display_name": "B", "email": "b@example.com", "password": PASSWORD})
        assert response.status_code == 403
        assert second.get("/api/meta").json()["allow_signup"] is False


def test_cross_site_writes_are_refused(client):
    evil = client.post("/api/foods", json=food(), headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert client.get("/api/foods").json()["total"] == 0
    same = client.post("/api/foods", json=food(), headers={"Origin": "http://testserver"})
    assert same.status_code == 201


# ---------------------------------------------------------------- privacy
def test_users_cannot_see_or_change_each_others_data(client, settings):
    mine = client.post("/api/foods", json=food(food_name="Owner milk", expiry_date="2026-10-25")).json()
    my_list = client.post("/api/shopping", json={"name": "Owner eggs"}).json()
    with make_client(settings) as other:
        register(other, "flatmate@example.com", "Flatmate")
        assert other.get("/api/foods").json()["total"] == 0
        assert other.get("/api/dashboard").json()["counts"]["total"] == 0
        assert other.get("/api/alerts").json()["active"] == 0
        assert other.get("/api/shopping").json()["counts"]["all"] == 0
        assert other.get("/api/analytics").json()["total"] == 0
        # Direct access by id behaves as if the item does not exist.
        assert other.get(f"/api/foods/{mine['id']}").status_code == 404
        assert other.put(f"/api/foods/{mine['id']}", json=food(food_name="hacked")).status_code == 404
        assert other.delete(f"/api/foods/{mine['id']}").status_code == 404
        assert other.post(f"/api/alerts/{mine['id']}/dismiss").status_code == 404
        assert other.put(f"/api/shopping/{my_list['id']}", json={"name": "hacked"}).status_code == 404
        assert other.patch(f"/api/shopping/{my_list['id']}/status", json={"purchased": True}).status_code == 404
        assert other.delete(f"/api/shopping/{my_list['id']}").status_code == 404
        assert other.post(f"/api/shopping/{my_list['id']}/move-to-inventory", json={"expiry_date": "2026-11-01"}).status_code == 404
        other.post("/api/shopping", json={"name": "Flatmate item"})
        other.patch(f"/api/shopping/{other.get('/api/shopping').json()['items'][0]['id']}/status", json={"purchased": True})
        other.post("/api/shopping/clear-completed")
        # Settings are per user.
        other.put("/api/settings", json={**other.get("/api/settings").json(), "expiry_threshold": 10, "theme": "dark"})
    assert client.get(f"/api/foods/{mine['id']}").json()["food_name"] == "Owner milk"
    assert client.get("/api/shopping").json()["items"][0]["name"] == "Owner eggs"
    assert client.get("/api/settings").json()["expiry_threshold"] == 3
    assert client.get("/api/settings").json()["theme"] == "system"


def test_idempotency_keys_are_per_user(client, settings):
    headers = {"Idempotency-Key": "shared-key-123"}
    owner_item = client.post("/api/foods", json=food(food_name="Mine"), headers=headers).json()
    with make_client(settings) as other:
        register(other, "b@example.com", "B")
        theirs = other.post("/api/foods", json=food(food_name="Theirs"), headers=headers)
        assert theirs.status_code == 201 and theirs.json()["id"] != owner_item["id"]
        assert theirs.json()["food_name"] == "Theirs"


def test_first_account_claims_existing_data_and_settings(tmp_path):
    from backend.config import load_settings
    from backend.db import connect
    from backend.migrations import migrate

    db = tmp_path / "food.db"
    conn = connect(db)
    migrate(conn, tmp_path / "b")
    conn.execute("INSERT INTO food(food_name, mfg_date, expiry_date, purchased_at, expires_at) VALUES ('Old rice', 'x', '2026-11-30', 'x', '2026-11-30')")
    conn.execute("UPDATE settings SET setting_value = '7' WHERE setting_key = 'expiry_threshold'")
    conn.close()
    cfg = replace(load_settings(), database_path=db, backup_dir=tmp_path / "b")
    with make_client(cfg) as owner:
        assert register(owner)["is_owner"] is True
        assert [i["food_name"] for i in owner.get("/api/foods").json()["items"]] == ["Old rice"]
        assert owner.get("/api/settings").json()["expiry_threshold"] == 7
    with make_client(cfg) as second:
        assert register(second, "b@example.com", "B")["is_owner"] is False
        assert second.get("/api/foods").json()["total"] == 0
        assert second.get("/api/settings").json()["expiry_threshold"] == 3
