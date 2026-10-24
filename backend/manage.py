"""Account administration for whoever runs the server.

    python -m backend.manage list-users
    python -m backend.manage reset-password someone@example.com

Works directly on the database, so it needs no running server and no recovery code.
"""
import argparse
import getpass
import sys

from .config import load_settings
from .db import connect
from .migrations import migrate
from .schemas import _password_rules
from .services.auth import owner_id, set_password_directly


def _ask_new_password(prompt=getpass.getpass):
    for _ in range(3):
        password = prompt("New password: ")
        try:
            _password_rules(password)
        except ValueError as error:
            print(f"  {error}. Try again.")
            continue
        if prompt("Type it again: ") != password:
            print("  The passwords don't match. Try again.")
            continue
        return password
    return None


def main(argv=None, prompt=getpass.getpass):
    parser = argparse.ArgumentParser(prog="python -m backend.manage", description="Food Expiry Tracker account administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list-users", help="show every account")
    reset = commands.add_parser("reset-password", help="set a new password for an account and sign it out everywhere")
    reset.add_argument("email")
    args = parser.parse_args(argv)

    settings = load_settings()
    conn = connect(settings.database_path)
    try:
        migrate(conn, settings.backup_dir)
        if args.command == "list-users":
            owner = owner_id(conn)
            rows = conn.execute("SELECT id, email, display_name, created_at, last_login_at FROM users ORDER BY id").fetchall()
            if not rows:
                print("No accounts yet. The first person to sign up becomes the owner.")
            for row in rows:
                role = " (owner)" if row["id"] == owner else ""
                print(f"{row['email']}{role}  name: {row['display_name']}  created: {row['created_at']}  last login: {row['last_login_at'] or 'never'}")
            return 0
        if not conn.execute("SELECT 1 FROM users WHERE email = ?", (args.email.strip().lower(),)).fetchone():
            print(f"No account uses {args.email}. Run 'list-users' to see accounts.")
            return 1
        password = _ask_new_password(prompt)
        if password is None:
            print("Password not changed.")
            return 1
        set_password_directly(conn, args.email, password)
        print(f"Password changed for {args.email.strip().lower()}. They have been signed out on every device.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
