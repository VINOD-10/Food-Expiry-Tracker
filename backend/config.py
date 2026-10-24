"""Centralised configuration, read once from environment variables."""
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_path: Path
    backup_dir: Path
    timezone_name: str
    cors_origins: tuple[str, ...]
    frontend_dir: Path

    @property
    def timezone(self):
        return ZoneInfo(self.timezone_name)


def load_settings():
    origins = os.environ.get("FOOD_CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    return Settings(
        database_path=Path(os.environ.get("FOOD_DB_PATH", PROJECT_ROOT / "food.db")),
        backup_dir=Path(os.environ.get("FOOD_BACKUP_DIR", PROJECT_ROOT / "backups")),
        timezone_name=os.environ.get("FOOD_TIMEZONE", "Asia/Kolkata"),
        cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
        frontend_dir=PROJECT_ROOT / "frontend",
    )
