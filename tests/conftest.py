import warnings
from dataclasses import replace
from datetime import date

import pytest

warnings.filterwarnings("ignore", message=".*httpx.*", category=DeprecationWarning)

from fastapi.testclient import TestClient  # noqa: E402

from backend.api.deps import get_today  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend.main import create_app  # noqa: E402

TODAY = date(2026, 10, 24)


@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), database_path=tmp_path / "food.db", backup_dir=tmp_path / "backups")


def make_client(settings, today=TODAY):
    app = create_app(settings)
    app.dependency_overrides[get_today] = lambda: today
    return TestClient(app, raise_server_exceptions=False)


PASSWORD = "correct horse battery"


def register(test_client, email="owner@example.com", name="Owner"):
    response = test_client.post("/api/auth/register", json={"display_name": name, "email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response.json()


def login(test_client, email="owner@example.com", password=PASSWORD):
    return test_client.post("/api/auth/login", json={"email": email, "password": password})


@pytest.fixture
def client(settings):
    """A client signed in as the first account (the owner)."""
    with make_client(settings) as test_client:
        register(test_client)
        yield test_client


def food(**overrides):
    payload = {"food_name": "Milk", "category": "Dairy", "quantity": 1, "unit": "L", "expiry_date": "2026-10-30"}
    payload.update(overrides)
    return payload
