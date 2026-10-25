import re
import shutil
import sqlite3

import pytest
from fastapi.testclient import TestClient

import run
from backend import manage
from backend.api.deps import get_today
from backend.main import create_app
from backend.services.auth import verify_password
from .conftest import PASSWORD, TODAY, login, make_client

CODE_PATTERN = re.compile(r"^[A-HJKMNP-Z2-9]{5}(-[A-HJKMNP-Z2-9]{5}){3}$")
NEW_PASSWORD = "a brand new password"


@pytest.fixture
def anon(settings):
    with make_client(settings) as test_client:
        yield test_client


def signup(test_client, email="owner@example.com"):
    response = test_client.post("/api/auth/register", json={"display_name": "Owner", "email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response.json()


def reset(test_client, code, email="owner@example.com", new_password=NEW_PASSWORD):
    return test_client.post("/api/auth/reset-password", json={"email": email, "recovery_code": code, "new_password": new_password})


def test_signup_returns_a_recovery_code_stored_only_as_a_hash(anon, settings):
    user = signup(anon)
    code = user["recovery_code"]
    assert CODE_PATTERN.match(code)
    assert user["has_recovery_code"] is True
    assert "recovery_code" not in anon.get("/api/auth/me").json(), "the code is shown once, at sign-up"
    stored = sqlite3.connect(settings.database_path).execute("SELECT recovery_hash FROM users").fetchone()[0]
    assert code.replace("-", "") not in stored and stored.startswith("scrypt$")


def test_reset_with_code_sets_new_password_and_issues_new_code(anon):
    code = signup(anon)["recovery_code"]
    anon.post("/api/auth/logout")

    response = reset(anon, code.lower().replace("-", " "))  # case, spaces and dashes don't matter
    assert response.status_code == 200, response.text
    new_code = response.json()["recovery_code"]
    assert CODE_PATTERN.match(new_code) and new_code != code
    assert anon.get("/api/foods").status_code == 200, "a reset logs the user in"

    anon.post("/api/auth/logout")
    assert login(anon).status_code == 401, "the old password no longer works"
    assert login(anon, password=NEW_PASSWORD).status_code == 200


def test_recovery_code_is_single_use(anon):
    code = signup(anon)["recovery_code"]
    assert reset(anon, code).status_code == 200
    assert reset(anon, code, new_password="yet another password").status_code == 401


def test_wrong_code_and_unknown_email_get_same_message(anon):
    signup(anon)
    wrong = reset(anon, "AAAAA-BBBBB-CCCCC-DDDDD")
    unknown = reset(anon, "AAAAA-BBBBB-CCCCC-DDDDD", email="nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"] == "That email and recovery code don't match"


def test_reset_validates_new_password(anon):
    code = signup(anon)["recovery_code"]
    response = reset(anon, code, new_password="short")
    assert response.status_code == 422
    assert "new_password" in response.json()["error"]["fields"]


def test_reset_attempts_are_throttled(anon):
    code = signup(anon)["recovery_code"]
    for _ in range(5):
        assert reset(anon, "AAAAA-BBBBB-CCCCC-DDDDD").status_code == 401
    assert reset(anon, code).status_code == 429, "even the right code is refused while throttled"


def test_reset_signs_out_every_other_session(settings):
    with make_client(settings) as first, make_client(settings) as second:
        code = signup(first)["recovery_code"]
        assert login(second).status_code == 200
        assert reset(second, code).status_code == 200
        assert first.get("/api/foods").status_code == 401
        assert second.get("/api/foods").status_code == 200


def test_regenerating_needs_the_password_and_replaces_the_old_code(anon):
    old = signup(anon)["recovery_code"]
    wrong = anon.post("/api/auth/recovery-code", json={"password": "not my password"})
    assert wrong.status_code == 422 and "password" in wrong.json()["error"]["fields"]

    response = anon.post("/api/auth/recovery-code", json={"password": PASSWORD})
    assert response.status_code == 200
    new = response.json()["recovery_code"]
    assert CODE_PATTERN.match(new) and new != old
    assert reset(anon, old).status_code == 401
    assert reset(anon, new).status_code == 200


def test_regenerating_requires_login(anon):
    assert anon.post("/api/auth/recovery-code", json={"password": PASSWORD}).status_code == 401


def test_accounts_from_before_recovery_codes_can_create_one(anon, settings):
    signup(anon)
    conn = sqlite3.connect(settings.database_path)
    conn.execute("UPDATE users SET recovery_hash = NULL")
    conn.commit()
    conn.close()
    assert anon.get("/api/auth/me").json()["has_recovery_code"] is False
    assert reset(anon, "AAAAA-BBBBB-CCCCC-DDDDD").status_code == 401

    assert anon.post("/api/auth/recovery-code", json={"password": PASSWORD}).status_code == 200
    assert anon.get("/api/auth/me").json()["has_recovery_code"] is True


# ---------- server command: python -m backend.manage ----------

@pytest.fixture
def manage_env(settings, monkeypatch):
    monkeypatch.setenv("FOOD_DB_PATH", str(settings.database_path))
    monkeypatch.setenv("FOOD_BACKUP_DIR", str(settings.backup_dir))
    return settings


def test_manage_list_users(anon, manage_env, capsys):
    signup(anon)
    signup(anon, "second@example.com")
    assert manage.main(["list-users"]) == 0
    out = capsys.readouterr().out
    assert "owner@example.com (owner)" in out and "second@example.com" in out


def test_manage_list_users_empty(manage_env, capsys):
    assert manage.main(["list-users"]) == 0
    assert "No accounts yet" in capsys.readouterr().out


def test_manage_reset_password_signs_user_out(anon, manage_env, capsys):
    signup(anon)
    answers = iter(["short", NEW_PASSWORD, "typo typo typo", NEW_PASSWORD, NEW_PASSWORD])
    assert manage.main(["reset-password", "Owner@Example.com"], prompt=lambda _: next(answers)) == 0
    assert "Password changed for owner@example.com" in capsys.readouterr().out
    assert anon.get("/api/foods").status_code == 401, "existing sessions are ended"
    stored = sqlite3.connect(manage_env.database_path).execute("SELECT password_hash FROM users").fetchone()[0]
    assert verify_password(NEW_PASSWORD, stored)


def test_manage_reset_password_gives_up_after_three_bad_tries(anon, manage_env, capsys):
    signup(anon)
    assert manage.main(["reset-password", "owner@example.com"], prompt=lambda _: "short") == 1
    assert "Password not changed" in capsys.readouterr().out
    assert login(anon).status_code == 200


def test_manage_reset_password_unknown_email(manage_env, capsys):
    assert manage.main(["reset-password", "nobody@example.com"], prompt=lambda _: pytest.fail("should not ask")) == 1
    assert "No account uses nobody@example.com" in capsys.readouterr().out


# ---------- HTTPS ----------

def https_client(settings):
    app = create_app(settings)
    app.dependency_overrides[get_today] = lambda: TODAY
    return TestClient(app, base_url="https://testserver", raise_server_exceptions=False)


def test_https_sends_hsts_and_secure_cookie(settings):
    with https_client(settings) as client:
        response = client.post("/api/auth/register", json={"display_name": "A", "email": "a@example.com", "password": PASSWORD})
        assert response.status_code == 201
        assert "secure" in response.headers["set-cookie"].lower()
        assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_plain_http_has_no_hsts_or_secure_cookie(anon):
    response = anon.post("/api/auth/register", json={"display_name": "A", "email": "a@example.com", "password": PASSWORD})
    assert "secure" not in response.headers["set-cookie"].lower()
    assert "strict-transport-security" not in response.headers


@pytest.mark.skipif(run.find_openssl() is None, reason="OpenSSL is not installed")
def test_make_cert_creates_certificate_and_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(run, "CERT_DIR", tmp_path / "certs")
    run.main(["--make-cert", "192.168.1.20"])
    cert, key = tmp_path / "certs" / "cert.pem", tmp_path / "certs" / "key.pem"
    assert cert.read_text().startswith("-----BEGIN CERTIFICATE-----")
    assert "PRIVATE KEY-----" in key.read_text()
    assert "192.168.1.20" in capsys.readouterr().out


def test_https_without_certificate_explains_how_to_make_one(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "CERT_DIR", tmp_path / "missing")
    monkeypatch.delenv("FOOD_SSL_CERTFILE", raising=False)
    monkeypatch.delenv("FOOD_SSL_KEYFILE", raising=False)
    with pytest.raises(SystemExit, match="--make-cert"):
        run.main(["--https"])


def test_certificate_folder_is_not_committed():
    assert "certs/" in open(run.ROOT / ".gitignore", encoding="utf-8").read().split()


def test_openssl_lookup_falls_back_to_git_for_windows(monkeypatch, tmp_path):
    fake = tmp_path / "openssl.exe"
    fake.write_text("")
    monkeypatch.setattr(shutil, "which", lambda _: None)
    monkeypatch.setattr(run, "GIT_OPENSSL", (tmp_path / "absent.exe", fake))
    assert str(run.find_openssl()) == str(fake)
