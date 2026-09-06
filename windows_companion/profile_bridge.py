"""Profile bridge that reuses Water Buddy's authoritative JSON store."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from water_buddy.clock import configure_timezone
from water_buddy.domain import add_water, dismiss_reminder, snooze_reminder
from water_buddy.pet import pet_snapshot
from water_buddy.storage import JsonStore


class ProfileBridge(Protocol):
    def snapshot(self) -> dict[str, Any]: ...
    def log_water(self, amount_ml: int) -> dict[str, Any]: ...
    def snooze(self, minutes: int = 10) -> None: ...
    def skip(self) -> None: ...
    def update_desktop_settings(self, **changes: Any) -> None: ...


class LocalJsonProfileBridge:
    """Local implementation; a future cloud bridge can implement the same protocol."""

    def __init__(self, path: str | Path) -> None:
        self.store = JsonStore(path)

    def _load(self) -> dict[str, Any]:
        data = self.store.load()
        prefs = data.get("preferences", {})
        configure_timezone(prefs.get("timezone"), prefs.get("timezone_offset_minutes"))
        return data

    def snapshot(self) -> dict[str, Any]:
        data = self._load()
        return {"data": data, "pet": pet_snapshot(data)}

    def log_water(self, amount_ml: int) -> dict[str, Any]:
        data = self._load()
        result = add_water(data, amount_ml, source="desktop mascot")
        self.store.save(data)
        return result

    def snooze(self, minutes: int = 10) -> None:
        data = self._load(); snooze_reminder(data, minutes); self.store.save(data)

    def skip(self) -> None:
        data = self._load(); dismiss_reminder(data); self.store.save(data)

    def update_desktop_settings(self, **changes: Any) -> None:
        data = self._load()
        settings = data.setdefault("preferences", {}).setdefault("desktop_pet", {})
        settings.update(changes)
        self.store.save(data)

