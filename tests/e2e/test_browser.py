"""Browser tests: real Chrome -> FastAPI -> SQLite.

Run with (PowerShell):  $env:RUN_E2E = "1"; python -m pytest tests/e2e
Uses the locally installed Chrome (or set E2E_BROWSER_CHANNEL=msedge).
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SCREENSHOTS = Path(os.environ.get("E2E_SCREENSHOTS", ROOT / "tests" / "e2e" / "screenshots"))
WIDTHS = [320, 375, 390, 430, 768, 1024, 1440, 1920]
pytestmark = pytest.mark.skipif(os.environ.get("RUN_E2E") != "1", reason="set RUN_E2E=1 to run browser tests")
PAGES = ["overview", "inventory", "add", "alerts", "shopping", "analytics", "settings"]


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Server:
    def __init__(self, db_path):
        self.db_path = db_path
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.proc = None

    def start(self):
        env = {**os.environ, "FOOD_DB_PATH": str(self.db_path), "FOOD_BACKUP_DIR": str(self.db_path.parent / "backups"),
               "FOOD_CORS_ORIGINS": self.url}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(self.port)],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                urllib.request.urlopen(f"{self.url}/api/health", timeout=1)
                return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("server did not start")

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)

    def api(self, method, path, body=None):
        request = urllib.request.Request(f"{self.url}{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    srv = Server(tmp_path_factory.mktemp("e2e") / "food.db")
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as pw:
        instance = pw.chromium.launch(channel=os.environ.get("E2E_BROWSER_CHANNEL", "chrome"))
        yield instance
        instance.close()


@pytest.fixture
def page(browser, server):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = context.new_page()
    pg.errors = []
    pg.on("pageerror", lambda error: pg.errors.append(str(error)))
    pg.on("console", lambda msg: msg.type == "error" and pg.errors.append(msg.text))
    pg.base = server.url
    yield pg
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    pg.screenshot(path=SCREENSHOTS / "last-test.png", full_page=True)
    context.close()
    assert not pg.errors, f"browser errors: {pg.errors}"


def iso(days):
    return (date.fromisoformat(today_str) + timedelta(days=days)).isoformat()


today_str = date.today().isoformat()


def go(page, route):
    page.goto(f"{page.base}/#/{route}")
    page.wait_for_load_state("networkidle")


def foods(server):
    return server.api("GET", "/api/foods?page_size=100")["items"]


# ------------------------------------------------------------------ tests
def test_navigation_and_empty_states(page, server):
    global today_str
    today_str = server.api("GET", "/api/meta")["today"]
    go(page, "overview")
    expect(page.get_by_role("heading", level=1)).to_have_text("Your kitchen at a glance")
    expect(page.get_by_text("Your inventory is empty")).to_be_visible()
    headings = {"inventory": "Your food inventory", "add": "Add a food item", "alerts": "Alert centre",
                "shopping": "Shopping list", "analytics": "Insights", "settings": "Settings", "overview": "Your kitchen at a glance"}
    for route, heading in headings.items():
        page.locator(f'#nav a[data-route="{route}"]').click()
        expect(page.get_by_role("heading", level=1)).to_have_text(heading)
        expect(page.locator(f'#nav a[data-route="{route}"]')).to_have_attribute("aria-current", "page")


def test_add_food_validation_and_double_submit(page, server):
    go(page, "add")
    page.get_by_role("button", name="Add to inventory").click()
    expect(page.locator("#ff-food_name-error")).to_have_text("Enter the food name")
    expect(page.locator("#ff-expiry_date-error")).to_have_text("Enter the expiry date")
    expect(page.locator("#ff-food_name")).to_be_focused()

    page.fill("#ff-food_name", "Greek yogurt")
    page.fill("#ff-expiry_date", iso(2))
    page.fill("#ff-mfg_date", iso(-1))
    page.fill("#ff-quantity", "0")
    page.get_by_role("button", name="Add to inventory").click()
    expect(page.locator("#ff-quantity-error")).to_have_text("Quantity must be greater than 0")

    page.fill("#ff-quantity", "2")
    page.select_option("#ff-category", "Dairy")
    page.select_option("#ff-storage_location", "Fridge")
    button = page.get_by_role("button", name="Add to inventory")
    button.dblclick()
    expect(page.locator(".toast").first).to_contain_text("Added Greek yogurt")
    expect(page.locator("#ff-food_name")).to_have_value("")
    assert [f["food_name"] for f in foods(server)] == ["Greek yogurt"], "double click must not duplicate"
    expect(page.locator("#alert-badge")).to_have_text("1")


def test_server_validation_preserves_input(page):
    go(page, "add")
    page.fill("#ff-food_name", "x" * 100)
    page.fill("#ff-expiry_date", "1999-01-01")
    page.get_by_role("button", name="Add to inventory").click()
    expect(page.locator("#ff-expiry_date-error")).to_contain_text("between 2000 and 2099")
    expect(page.locator("#ff-food_name")).to_have_value("x" * 100)


def test_inventory_crud_filters_and_dashboard_refresh(page, server):
    for name, category, days in [("Apples", "Fruits", 10), ("Bread", "Grains", 0), ("Cheddar", "Dairy", -3), ("<img src=x onerror=alert(1)>", "Other", 30)]:
        server.api("POST", "/api/foods", {"food_name": name, "category": category, "expiry_date": iso(days)})
    go(page, "inventory")
    rows = page.locator("table.data-table tbody tr")
    expect(rows).to_have_count(5)
    expect(page.get_by_text("<img src=x onerror=alert(1)>")).to_be_visible()  # rendered as text, not HTML
    assert page.locator("table img").count() == 0

    page.fill("#f-search", "che")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Cheddar")
    page.get_by_role("button", name="Clear filters").click()
    expect(rows).to_have_count(5)
    page.select_option("#f-category", "Fruits")
    expect(rows).to_have_count(1)
    page.select_option("#f-category", "")
    page.select_option("#f-status", "expired")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Expired 3 days ago")
    page.select_option("#f-status", "")
    page.select_option("#f-sort", "name")
    expect(rows.first).to_contain_text("<img")
    page.select_option("#f-sort", "expiry")
    expect(rows.first).to_contain_text("Cheddar")

    # Edit opens pre-filled and updates in place.
    page.get_by_role("button", name="Edit Bread").click()
    dialog = page.locator("dialog.modal")
    expect(dialog.locator("#ff-food_name")).to_have_value("Bread")
    dialog.locator("#ff-food_name").fill("Brown bread")
    dialog.locator("#ff-expiry_date").fill(iso(20))
    dialog.get_by_role("button", name="Save changes").click()
    expect(dialog).to_have_count(0)
    expect(page.get_by_text("Saved changes to Brown bread")).to_be_visible()
    expect(rows).to_have_count(5)
    assert len(foods(server)) == 5

    # Cancelled delete keeps the item; confirmed delete removes it.
    page.get_by_role("button", name="Delete Cheddar").click()
    page.locator("dialog.modal").get_by_role("button", name="Cancel").click()
    expect(rows).to_have_count(5)
    page.get_by_role("button", name="Delete Cheddar").click()
    page.locator("dialog.modal").get_by_text("Thrown away").click()
    page.locator("dialog.modal").get_by_role("button", name="Delete item").click()
    expect(rows).to_have_count(4)
    assert "Cheddar" not in [f["food_name"] for f in foods(server)]

    go(page, "overview")
    stats = page.locator(".stats")
    expect(stats.locator(".tone-total .stat-value")).to_have_text("4")
    expect(stats.locator(".tone-expired .stat-value")).to_have_text("0")
    expect(stats.locator(".tone-soon .stat-value")).to_have_text("1")  # yogurt
    assert page.get_by_role("button", name="Edit").count() == 0, "overview must not offer editing"
    assert page.locator("text=Update").count() == 0


def test_alerts_dismiss_restore_and_threshold(page, server):
    go(page, "alerts")
    cards = page.locator(".alert-card")
    expect(cards).to_have_count(1)
    expect(cards.first).to_contain_text("Greek yogurt")
    cards.first.get_by_role("button", name="View").click()
    expect(page.locator("dialog.modal")).to_contain_text("Days remaining")
    page.keyboard.press("Escape")
    cards.first.get_by_role("button", name="Dismiss alert for Greek yogurt").click()
    expect(page.get_by_text("You're all caught up")).to_be_visible()
    expect(page.locator("#alert-badge")).to_be_hidden()
    page.get_by_label("Show dismissed alerts").check()
    page.get_by_role("button", name="Restore alert for Greek yogurt").click()
    expect(page.locator("#alert-badge")).to_have_text("1")

    page.fill("#threshold", "15")
    page.get_by_role("button", name="Update").click()
    expect(page.get_by_text("Alert window set to 15 days")).to_be_visible()
    expect(page.locator(".alert-card")).to_have_count(2)  # yogurt + apples (10 days)
    page.fill("#threshold", "3")
    page.get_by_role("button", name="Update").click()
    expect(page.locator(".alert-card")).to_have_count(1)

    # Editing the expiry date updates the alert.
    page.locator(".alert-card").first.get_by_role("link", name="Open in inventory").click()
    expect(page.locator("tr.highlight")).to_contain_text("Greek yogurt")
    page.get_by_role("button", name="Edit Greek yogurt").click()
    page.locator("dialog.modal #ff-expiry_date").fill(iso(-1))
    page.locator("dialog.modal").get_by_role("button", name="Save changes").click()
    go(page, "alerts")
    expect(page.locator(".alert-card").first).to_contain_text("Expired 1 day ago")


def test_shopping_list_flow(page, server):
    go(page, "shopping")
    page.get_by_role("button", name="Add item").click()
    expect(page.locator('[data-error="name"]')).to_have_text("Enter an item name")
    for name in ("Eggs", "Rice"):
        page.fill("#new-name", name)
        page.fill("#new-qty", "2")
        page.get_by_role("button", name="Add item").click()
        expect(page.locator(".shop-list li", has_text=name)).to_be_visible()
    page.get_by_role("checkbox", name="Mark as purchased: Eggs").click()
    expect(page.get_by_role("checkbox", name="Mark as pending: Eggs")).to_have_attribute("aria-checked", "true")
    page.locator('[data-filter="pending"]').click()
    expect(page.locator(".shop-list li")).to_have_count(1)
    page.locator('[data-filter="all"]').click()

    page.get_by_role("button", name="Edit Rice").click()
    page.locator("dialog.modal #edit-name").fill("Basmati rice")
    page.locator("dialog.modal").get_by_role("button", name="Save changes").click()
    expect(page.locator(".shop-list li", has_text="Basmati rice")).to_be_visible()

    page.locator(".shop-list li", has_text="Eggs").get_by_role("button", name="Add to inventory").click()
    dialog = page.locator("dialog.modal")
    dialog.get_by_role("button", name="Add to inventory").click()
    expect(dialog.locator('[data-error="expiry_date"]')).to_have_text("Enter the expiry date")
    dialog.locator("#mv-exp").fill(iso(14))
    dialog.get_by_role("button", name="Add to inventory").click()
    expect(page.locator(".shop-list li", has_text="Eggs")).to_contain_text("In inventory")
    assert "Eggs" in [f["food_name"] for f in foods(server)]

    page.get_by_role("button", name="Clear purchased").click()
    page.locator("dialog.modal").get_by_role("button", name="Clear purchased").click()
    expect(page.locator(".shop-list li")).to_have_count(1)
    page.get_by_role("button", name="Delete Basmati rice").click()
    page.locator("dialog.modal").get_by_role("button", name="Delete").click()
    expect(page.get_by_text("Your shopping list is empty")).to_be_visible()


def test_analytics_uses_real_data(page):
    go(page, "analytics")
    expect(page.get_by_role("heading", name="Expiry status breakdown")).to_be_visible()
    expect(page.locator(".stats .tone-total .stat-value")).to_have_text("5")
    waste = page.locator("section", has=page.get_by_role("heading", name="Waste insights"))
    expect(waste).to_contain_text("100% of removed food with a known outcome was thrown away")
    page.locator(".hbar .bar").first.hover()
    expect(page.locator("#tooltip")).to_be_visible()


def test_settings_persist_across_reload(page, server):
    go(page, "settings")
    page.select_option("#s-date", "%Y-%m-%d")
    page.get_by_text("Dark", exact=True).click()
    page.get_by_role("button", name="Save settings").click()
    expect(page.get_by_text("Settings saved.")).to_be_visible()
    page.reload()
    page.wait_for_load_state("networkidle")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert server.api("GET", "/api/settings")["date_format"] == "%Y-%m-%d"
    go(page, "inventory")
    expect(page.locator("table.data-table")).to_contain_text(iso(10))
    go(page, "settings")
    page.select_option("#s-date", "%d-%m-%Y")
    page.get_by_text("Match device").click()
    page.get_by_role("button", name="Save settings").click()
    expect(page.get_by_text("Settings saved.")).to_be_visible()


def test_api_failure_shows_retry(page):
    page.route("**/api/dashboard", lambda route: route.abort())
    page.goto(f"{page.base}/#/overview")
    expect(page.get_by_text("Couldn't load this page")).to_be_visible()
    page.unroute("**/api/dashboard")
    page.get_by_role("button", name="Try again").click()
    expect(page.get_by_role("heading", level=1)).to_have_text("Your kitchen at a glance")
    page.errors.clear()  # the aborted request logs an expected console error


def test_responsive_layouts_have_no_horizontal_overflow(browser, server):
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    problems = []
    for width in WIDTHS:
        context = browser.new_context(viewport={"width": width, "height": 860})
        pg = context.new_page()
        for route in PAGES:
            pg.goto(f"{server.url}/#/{route}")
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(150)
            overflow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if overflow > 0:
                problems.append(f"{route}@{width}px overflows by {overflow}px")
            clipped = pg.evaluate("""() => [...document.querySelectorAll('button, a.btn')].filter(b => !b.closest('#sidebar')).filter(b => {
                const r = b.getBoundingClientRect(); return r.width && (r.right > innerWidth + 1 || r.left < -1); }).map(b => b.textContent.trim()).slice(0, 3)""")
            if clipped:
                problems.append(f"{route}@{width}px clipped controls: {clipped}")
            if width in (320, 390, 768, 1440):
                # Full-page capture mis-renders the sticky desktop sidebar, so desktop shots use the viewport.
                pg.screenshot(path=SCREENSHOTS / f"{route}-{width}.png", full_page=width < 900)
        context.close()
    assert not problems, "; ".join(problems)


def test_mobile_menu_and_card_layout(browser, server):
    context = browser.new_context(viewport={"width": 375, "height": 800})
    pg = context.new_page()
    pg.goto(f"{server.url}/#/overview")
    menu = pg.get_by_role("button", name="Open menu")
    expect(menu).to_be_visible()
    expect(pg.locator("#sidebar")).not_to_be_in_viewport()
    menu.click()
    expect(menu).to_have_attribute("aria-expanded", "true")
    pg.locator('#nav a[data-route="inventory"]').click()
    expect(pg.get_by_role("heading", level=1)).to_have_text("Your food inventory")
    expect(menu).to_have_attribute("aria-expanded", "false")
    # Cards rather than a table header on small screens, with labelled actions.
    expect(pg.locator(".data-table thead")).to_be_hidden()
    expect(pg.get_by_role("button", name="Edit Apples")).to_be_visible()
    box = pg.get_by_role("button", name="Edit Apples").bounding_box()
    assert box["height"] >= 44, "touch target too small"
    context.close()


def test_data_persists_after_server_restart(server):
    before = {f["id"]: f["food_name"] for f in foods(server)}
    server.stop()
    server.start()
    assert {f["id"]: f["food_name"] for f in foods(server)} == before
