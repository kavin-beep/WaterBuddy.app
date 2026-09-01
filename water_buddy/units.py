"""Canonical volume conversion and display helpers for Water Buddy."""

from __future__ import annotations

import math
from typing import Final

ML_PER_US_FL_OUNCE: Final[float] = 29.5735


def normalize_units(units: object) -> str:
    """Return the supported display-unit token for an arbitrary value."""

    token = str(units).strip().casefold()
    if token in {"oz", "fl oz", "floz", "fluid ounces"}:
        return "oz"
    if token in {"l", "liter", "liters", "litre", "litres"}:
        return "l"
    return "ml"


def unit_label(units: object) -> str:
    """Return a human-readable label for the selected display units."""

    normalized = normalize_units(units)
    if normalized == "oz":
        return "fl oz"
    return "L" if normalized == "l" else "ml"


def from_millilitres(amount_ml: object, units: object = "ml") -> float:
    """Convert a canonical millilitre amount into the requested display units."""

    if isinstance(amount_ml, bool):
        return 0.0
    try:
        amount = float(amount_ml)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(amount):
        return 0.0
    amount = max(0.0, amount)
    normalized = normalize_units(units)
    if normalized == "oz":
        return amount / ML_PER_US_FL_OUNCE
    return amount / 1000 if normalized == "l" else amount


def to_millilitres(amount: object, units: object = "ml") -> int:
    """Convert a non-negative display amount into canonical millilitres."""

    if isinstance(amount, bool):
        raise ValueError(  # noqa: TRY004 - invalid user value, not an API type contract
            "Volume must be a finite non-negative number."
        )
    try:
        numeric = float(amount)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Volume must be a finite non-negative number.") from error
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError("Volume must be a finite non-negative number.")
    normalized = normalize_units(units)
    if normalized == "oz":
        numeric *= ML_PER_US_FL_OUNCE
    elif normalized == "l":
        numeric *= 1000
    return round(numeric)


def format_volume(amount_ml: object, units: object = "ml") -> str:
    """Format a canonical millilitre amount in the selected display units."""

    normalized = normalize_units(units)
    if normalized == "oz":
        ounces = from_millilitres(amount_ml, "oz")
        return f"{ounces:.1f}".rstrip("0").rstrip(".") + " fl oz"
    if normalized == "l":
        litres = from_millilitres(amount_ml, "l")
        precision = 2 if 0 < litres < 1 else 1
        return f"{litres:.{precision}f}".rstrip("0").rstrip(".") + " L"
    amount = round(from_millilitres(amount_ml, "ml"))
    return f"{amount:,} ml"


__all__ = [
    "ML_PER_US_FL_OUNCE",
    "format_volume",
    "from_millilitres",
    "normalize_units",
    "to_millilitres",
    "unit_label",
]
