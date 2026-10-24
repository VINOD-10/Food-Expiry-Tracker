"""Request validation and response models."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CATEGORIES = (
    "Fruits", "Vegetables", "Dairy", "Grains", "Meat and seafood",
    "Packaged food", "Beverages", "Frozen food", "Other",
)
UNITS = ("pcs", "g", "kg", "ml", "L", "pack", "dozen", "bottle", "can", "box")
STORAGE_LOCATIONS = ("Fridge", "Freezer", "Pantry", "Cupboard", "Counter", "Other")
DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d %b %Y")
SORTS = ("Expiry date", "Newest", "Name")
THEMES = ("system", "light", "dark")
MIN_DATE = date(2000, 1, 1)
MAX_DATE = date(2099, 12, 31)

Category = Literal[CATEGORIES]
Unit = Literal[UNITS]


def _clean_text(value):
    if value is None:
        return None
    value = " ".join(str(value).split())
    return value or None


def _name(cls, value):
    return _clean_text(value) or "" if isinstance(value, str) or value is None else value


def _notes(cls, value):
    return (value.strip() or None) if isinstance(value, str) else value


def _blank_is_none(cls, value):
    return None if value == "" else value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FoodIn(StrictModel):
    food_name: str = Field(min_length=1, max_length=100)
    category: Category = "Other"
    quantity: float | None = Field(default=None, gt=0, le=100000)
    unit: Unit | None = None
    mfg_date: date | None = None
    expiry_date: date
    storage_location: Literal[STORAGE_LOCATIONS] | None = None
    notes: str | None = Field(default=None, max_length=500)

    _clean_name = field_validator("food_name", mode="before")(_name)
    _clean_notes = field_validator("notes", mode="before")(_notes)
    _blanks = field_validator("unit", "storage_location", "mfg_date", mode="before")(_blank_is_none)

    @model_validator(mode="after")
    def _check_dates(self):
        for label, value in (("Expiry date", self.expiry_date), ("Manufacturing date", self.mfg_date)):
            if value is not None and not MIN_DATE <= value <= MAX_DATE:
                raise ValueError(f"{label} must be between {MIN_DATE.year} and {MAX_DATE.year}")
        if self.mfg_date and self.mfg_date > self.expiry_date:
            raise ValueError("Manufacturing date cannot be after the expiry date")
        if self.quantity is not None and self.unit is None:
            self.unit = "pcs"
        return self


class ShoppingIn(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: float | None = Field(default=None, gt=0, le=100000)
    unit: Unit | None = None
    category: Category = "Other"
    notes: str | None = Field(default=None, max_length=500)

    _clean_name = field_validator("name", mode="before")(_name)
    _clean_notes = field_validator("notes", mode="before")(_notes)
    _blanks = field_validator("unit", mode="before")(_blank_is_none)


class ShoppingStatusIn(StrictModel):
    purchased: bool


class MoveToInventoryIn(StrictModel):
    expiry_date: date
    mfg_date: date | None = None
    category: Category | None = None
    quantity: float | None = Field(default=None, gt=0, le=100000)
    unit: Unit | None = None
    storage_location: Literal[STORAGE_LOCATIONS] | None = None

    _blanks = field_validator("unit", "storage_location", "mfg_date", "category", mode="before")(_blank_is_none)


class SettingsIn(StrictModel):
    expiry_threshold: int = Field(ge=0, le=30)
    date_format: Literal[DATE_FORMATS]
    default_sort: Literal[SORTS]
    theme: Literal[THEMES]
    browser_notifications: bool


RemovalReason = Literal["consumed", "discarded", "other"]
