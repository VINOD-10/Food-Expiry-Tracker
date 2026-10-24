# Food Expiry Tracker

A responsive web app for tracking groceries and expiry dates, built for students, hostel residents and anyone managing food on a budget. It runs on a FastAPI backend with a local SQLite database. The original Tkinter desktop app (`app.py`) still works on the same database.

## Features

| Page | What you can do |
|---|---|
| **Log in / Sign up** | Create an account or log in. Each account has its own private inventory, shopping list, alerts and settings. Includes a show/hide password toggle and a "keep me logged in for 30 days" option. |
| **Overview** | See summary counts, a priority alert banner, the items needing attention, the expiry distribution, recently added items and waste-prevention tips. This page is read-only; editing happens in Inventory. |
| **Inventory** | Edit and delete items (with confirmation), search by name, filter by category or status, sort by expiry date, newest or name, and page through results. The table becomes cards on phones. |
| **Add Food** | Add an item with validation. Only the name and expiry date are required. Food that has already expired is accepted. |
| **Expiry Alerts** | See alerts grouped as Expired, Expires today and Expiring soon. View details, jump to the item in the inventory, dismiss or restore an alert, and change the alert window. |
| **Shopping List** | Add, edit and delete items, mark them purchased or pending, filter, and clear purchased items. A purchased item can be added to the inventory once you enter its expiry date. |
| **Analytics** | See status and category breakdowns, monthly additions and waste insights (used vs. thrown away), all from recorded data, with a table view for each chart. |
| **Settings** | Set the alert threshold, browser notifications (opt-in, only while the app is open), date format, default sort and theme (system, light or dark). |

### How expiry status works

Status is worked out on the backend only, by calendar date in the app timezone (default `Asia/Kolkata`):

- **Expired**: the expiry date is before today
- **Expires today**: the expiry date is today
- **Expiring soon**: within the threshold (default 3 days, configurable from 0 to 30)
- **Safe**: more than the threshold away

Status is based only on the printed date. It does not mean the food is safe to eat.

The desktop app uses these same rules and the same threshold, so both apps always show the same status. When you delete an item in the desktop app, it asks what happened to the food (used or eaten, thrown away, other) and records the answer for the web app's waste insights.

## Run it (Windows PowerShell)

```powershell
cd C:\Users\vinod\FoodExpiryTracker
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # first time only
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. The same server serves the frontend and the API, so there is no separate build or frontend server. Interactive API docs are at http://127.0.0.1:8000/docs.

The desktop app still works:

```powershell
python app.py
```

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `FOOD_DB_PATH` | `food.db` in the project root | SQLite database file |
| `FOOD_BACKUP_DIR` | `backups\` | Where pre-migration backups are written |
| `FOOD_TIMEZONE` | `Asia/Kolkata` | Timezone that defines "today" |
| `FOOD_CORS_ORIGINS` | `http://127.0.0.1:8000,http://localhost:8000` | Comma-separated list of allowed browser origins |
| `FOOD_ALLOW_SIGNUP` | `true` | Set to `false` to stop new sign-ups once everyone has an account. The first (owner) account can always be created. |

Example: `$env:FOOD_TIMEZONE = "Europe/London"; uvicorn backend.main:app`

There are no secrets to configure.

## Accounts and security

- **The first account you create is the owner.** It takes over any data that existed before accounts, plus the old settings. The desktop app (`python app.py`) has no login, so it always shows the owner's inventory and uses the owner's settings. Items added in the desktop app belong to the owner.
- **Each account's data is private.** Every database query is filtered by the logged-in user. Asking for another person's item by its ID gets "not found", exactly as if it didn't exist.
- **Passwords** must be 8–128 characters. They are hashed with scrypt and a random salt (Python standard library) and never stored or logged in plain text.
- **Sessions** last 7 days, or 30 with "keep me logged in". The session token is in an `HttpOnly`, `SameSite=Lax` cookie, which page scripts can't read. The database stores only a SHA-256 hash of it. Logging out ends the session on the server. Changing your password signs out your other devices.
- **Brute-force protection:** after 5 wrong passwords for one email (or 30 from one IP address) within 15 minutes, logins are refused until the 15 minutes pass. A wrong password and an unknown email get the same message, so the login page doesn't reveal who has an account.
- **Cross-site protection:** writes (POST, PUT, PATCH, DELETE) that come from another website are refused, on top of the `SameSite` cookie.
- **Not included:** password reset by email (the app sends no email). A forgotten password can only be reset by someone with access to the database file. If you ever put the app on a network, serve it over HTTPS; the cookie is then marked `Secure` automatically.

## Database and migrations

- The existing `food.db` is kept as it is. Schema changes are **additive only**: new columns on `food` and new tables. Nothing is dropped or rewritten.
- Migrations live in `backend/migrations.py` and run automatically at startup. Applied versions are recorded in the `schema_migrations` table.
- Before any pending migration runs, the database is copied to `backups\food-pre-migration-v<N>-<timestamp>.db` using SQLite's backup API. The copy is checked with `PRAGMA integrity_check` and per-table row counts.
- Each migration runs in its own transaction. If one fails, it is rolled back.
- **Restore a backup:** stop the server, then run `Copy-Item backups\<file>.db food.db -Force`.

| Version | Change |
|---|---|
| 1 | Baseline: the desktop app's `food` and `settings` tables |
| 2 | `food` gets `category`, `quantity`, `unit`, `storage_location`, `notes`, `created_at` and `updated_at`, plus indexes and timestamp triggers so desktop-app inserts get timestamps too |
| 3 | `shopping_items` table (foreign key to `food`, `ON DELETE SET NULL`) |
| 4 | `alert_dismissals` (foreign key, `ON DELETE CASCADE`), `food_removals` (history for waste insights), `idempotency_keys` (prevents duplicate records from double submission) |
| 5 | Default values for the new settings. Existing settings are never overwritten. |
| 6 | Accounts: `users`, `sessions`, `auth_failures` and `user_settings` tables; a `user_id` owner column on `food`, `shopping_items`, `food_removals` and `idempotency_keys`; triggers so rows added by the desktop app belong to the owner |

Foreign keys are enabled on every connection.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/meta` | Categories, units, storage locations, timezone and today's date |
| GET | `/api/foods` | List items. Takes `search`, `category`, `status` (`expired`/`today`/`soon`/`safe`/`unknown`/`attention`), `sort` (`expiry`/`newest`/`name`), `page` and `page_size`. |
| POST | `/api/auth/register` | Create an account and log in |
| POST | `/api/auth/login` | Log in. Body: `email`, `password`, optional `remember`. |
| POST | `/api/auth/logout` | Log out |
| GET | `/api/auth/me` | The logged-in user, or 401 |
| PUT | `/api/auth/password` | Change password. Signs out other devices. |
| POST | `/api/foods` | Create an item. An optional `Idempotency-Key` header makes retries safe. |
| GET / PUT / DELETE | `/api/foods/{id}` | Get, update or delete an item. DELETE takes `?reason=consumed\|discarded\|other`. |
| GET | `/api/dashboard` | Overview counts, the attention list and recent items |
| GET | `/api/alerts` | Alerts. Add `?include_dismissed=true` to include dismissed ones. |
| POST / DELETE | `/api/alerts/{id}/dismiss` | Dismiss or restore an alert. A dismissal resets automatically if the item's status or expiry date changes. |
| GET / POST | `/api/shopping` | List items (`?status=all\|pending\|purchased`) or create one |
| PUT / DELETE | `/api/shopping/{id}` | Update or delete a shopping item |
| PATCH | `/api/shopping/{id}/status` | Mark purchased or pending: `{"purchased": true}` |
| POST | `/api/shopping/clear-completed` | Delete all purchased items |
| POST | `/api/shopping/{id}/move-to-inventory` | Create an inventory item. The expiry date is required. |
| GET | `/api/analytics` | Analytics computed from stored data |
| GET / PUT | `/api/settings` | Read or update your settings |

Everything except `/api/health`, `/api/meta`, register and login requires you to be logged in; otherwise the API answers 401.

Errors use one shape: `{"error": {"code", "message", "fields"}}`. Stack traces are never returned.

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest                                    # backend: API, expiry engine, migrations

$env:RUN_E2E = "1"; python -m pytest tests/e2e      # browser tests in your installed Chrome
```

Optional accessibility audit (WCAG 2.1 A/AA, using axe-core). It needs Node.js:

```powershell
npm install --prefix $env:TEMPxe axe-core@4.10.2
$env:AXE_CORE_PATH = "$env:TEMPxe
ode_modulesxe-corexe.min.js"
$env:RUN_E2E = "1"; python -m pytest tests/e2e -k accessibility
```

The browser suite starts a real server on a temporary database. It checks navigation, every form, CRUD, filters, alerts, the shopping flow, settings persistence, API-failure handling and XSS escaping. It also covers browser notifications (granted, refused and blocked permission) and checks for horizontal overflow and clipped controls at 320, 375, 390, 430, 768, 1024, 1440 and 1920 px. Screenshots are saved to `tests/e2e/screenshots/`. To use Edge instead, set `$env:E2E_BROWSER_CHANNEL = "msedge"`.

## Project layout

```
app.py, database.py, expiry.py   original desktop app (now shares backend/expiry_engine.py)
backend/
  main.py          FastAPI app, error handlers, security headers, static frontend
  config.py        environment configuration
  db.py            SQLite connections and transactions
  migrations.py    versioned additive migrations with verified backups
  expiry_engine.py the single source of expiry status
  schemas.py       Pydantic validation
  api/             route modules
  services/        business logic (foods, shopping, analytics, settings)
frontend/          HTML, CSS and JavaScript modules (no build step)
tests/             pytest suites; tests/e2e has the browser tests
```
