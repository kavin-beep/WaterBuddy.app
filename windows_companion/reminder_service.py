"""Reminder evaluation with recent-log suppression."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, MutableMapping

from water_buddy.domain import reminder_is_due


def last_log_at(data: Mapping[str, Any], now: datetime) -> datetime | None:
    record = data.get("daily_records", {}).get(now.date().isoformat(), {})
    entries = record.get("entries", []) if isinstance(record, Mapping) else []
    values: list[datetime] = []
    for entry in entries if isinstance(entries, list) else []:
        try:
            values.append(datetime.fromisoformat(str(entry["logged_at"])))
        except (KeyError, TypeError, ValueError):
            pass
    return max(values, default=None)


def should_notify(data: MutableMapping[str, Any], now: datetime) -> bool:
    settings = data.get("preferences", {}).get("desktop_pet", {})
    if not settings.get("enabled", False) or not settings.get("reminders_enabled", True):
        return False
    recent = last_log_at(data, now)
    suppression = int(settings.get("recent_log_suppression_minutes", 10))
    if recent is not None and 0 <= (now - recent).total_seconds() < suppression * 60:
        return False
    return reminder_is_due(data, now)

