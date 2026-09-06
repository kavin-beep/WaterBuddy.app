"""Pure models shared by the companion UI and tests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from water_buddy.domain import normalize_desktop_pet_settings


class MascotState(str, Enum):
    IDLE = "idle"
    ENTRANCE = "entrance"
    WAVE = "wave"
    HAPPY = "happy"
    THIRST_REMINDER = "thirst_reminder"
    TALK = "talk"
    SLEEP = "sleep"
    CELEBRATE = "celebrate"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class DesktopPetSettings:
    enabled: bool = False
    always_on_top: bool = True
    scale: float = 1.0
    motion_enabled: bool = True
    sound_enabled: bool = True
    reminders_enabled: bool = True
    recent_log_suppression_minutes: int = 10
    position: tuple[int, int] | None = None
    monitor: str | None = None

    @classmethod
    def from_mapping(cls, value: object) -> "DesktopPetSettings":
        safe = normalize_desktop_pet_settings(value)
        point = safe["position"]
        return cls(
            enabled=safe["enabled"], always_on_top=safe["always_on_top"],
            scale=safe["scale"], motion_enabled=safe["motion_enabled"],
            sound_enabled=safe["sound_enabled"], reminders_enabled=safe["reminders_enabled"],
            recent_log_suppression_minutes=safe["recent_log_suppression_minutes"],
            position=(point["x"], point["y"]) if point else None, monitor=safe["monitor"],
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled, "always_on_top": self.always_on_top,
            "scale": self.scale, "motion_enabled": self.motion_enabled,
            "sound_enabled": self.sound_enabled, "reminders_enabled": self.reminders_enabled,
            "recent_log_suppression_minutes": self.recent_log_suppression_minutes,
            "position": ({"x": self.position[0], "y": self.position[1]} if self.position else None),
            "monitor": self.monitor,
        }


def next_state(current: MascotState, event: str) -> MascotState:
    """Explicit, deterministic animation state transitions."""
    if event == "disable":
        return MascotState.HIDDEN
    if event == "enable":
        return MascotState.ENTRANCE
    if event == "water_logged":
        return MascotState.HAPPY
    if event == "goal_reached":
        return MascotState.CELEBRATE
    if event == "reminder_due":
        return MascotState.THIRST_REMINDER
    if event == "clicked":
        return MascotState.TALK
    if event == "double_clicked":
        return MascotState.WAVE
    if event == "quiet_hours":
        return MascotState.SLEEP
    if event == "animation_complete":
        return MascotState.IDLE if current != MascotState.HIDDEN else current
    return current

