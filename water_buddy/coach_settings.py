"""Allowlisted FLOW settings proposals and account-local persistence."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import timedelta
import re

from water_buddy.clock import local_now
from water_buddy.domain import THEME_OPTIONS, calculate_goal, set_daily_goal
from water_buddy.pet import rename_pet


@dataclass(frozen=True)
class SettingsProposal:
    changes: dict


# Each field maps to an existing setting. No paths, accounts, or secrets are accepted.
FIELDS = {
    "theme": ("preferences", "theme", "Theme"),
    "units": ("preferences", "units", "Volume display"),
    "reminders_enabled": ("preferences", "reminders_enabled", "Reminders"),
    "reminder_interval_minutes": ("preferences", "reminder_interval_minutes", "Reminder interval"),
    "quiet_start": ("preferences", "quiet_start", "Quiet hours start"),
    "quiet_end": ("preferences", "quiet_end", "Quiet hours end"),
    "sound_enabled": ("preferences", "sound_enabled", "Interface sounds"),
    "background_motion": ("preferences", "background_motion", "Background motion"),
    "interface_sound_volume": ("preferences", "interface_sound_volume", "Click volume"),
    "daily_goal_ml": ("profile", "manual_goal_ml", "Daily goal"),
    "display_name": ("profile", "name", "Display name"),
    "pet_name": ("profile", "mascot_name", "Pet name"),
    "wake_time": ("profile", "wake_time", "Wake time"),
    "sleep_time": ("profile", "sleep_time", "Sleep time"),
}
INTERVALS = [15, 30, 45, 60, 90, 120]
ENUMS = {"theme": list(THEME_OPTIONS), "units": ["ml", "oz"],
         "reminder_interval_minutes": INTERVALS,
         "interface_sound_volume": ["Soft", "Balanced", "Vivid"]}
BOOLEANS = {"reminders_enabled", "sound_enabled", "background_motion"}
CLOCKS = {"quiet_start", "quiet_end", "wake_time", "sleep_time"}


def _properties():
    properties = {}
    for name in FIELDS:
        if name in ENUMS:
            properties[name] = {"type": "integer" if name == "reminder_interval_minutes" else "string", "enum": ENUMS[name]}
        elif name in BOOLEANS:
            properties[name] = {"type": "boolean"}
        elif name in CLOCKS:
            properties[name] = {"type": "string", "description": "24-hour local time, HH:MM", "pattern": r"^([01][0-9]|2[0-3]):[0-5][0-9]$"}
        elif name == "daily_goal_ml":
            properties[name] = {"type": ["integer", "null"], "minimum": 500, "maximum": 8000,
                                "description": "Explicit user-chosen daily goal in whole millilitres. Convert litres to ml; null restores automatic goal. Never invent a medical target."}
        else:
            properties[name] = {"type": "string", "minLength": 1, "maxLength": 24 if name == "pet_name" else 48}
    return properties


SETTINGS_TOOL = {
    "type": "function",
    "function": {
        "name": "prepare_settings_update",
        "description": "Prepare ONLY settings explicitly requested by the user. This does not save: the user must click Apply changes. Omit every unchanged or unspecified field. Ask for clarification for ambiguous values or unsupported intervals; never substitute a different value.",
        "parameters": {"type": "object", "properties": _properties(), "minProperties": 1, "additionalProperties": False},
    },
}


def validate_changes(changes):
    if not isinstance(changes, dict) or not changes or set(changes) - FIELDS.keys():
        raise ValueError("Only supported profile and preference settings can be changed.")
    clean = {}
    for name, value in changes.items():
        if name in ENUMS:
            if type(value) is not (int if name == "reminder_interval_minutes" else str) or value not in ENUMS[name]:
                raise ValueError(f"{FIELDS[name][2]} must be one of: {', '.join(map(str, ENUMS[name]))}.")
        elif name in BOOLEANS:
            if type(value) is not bool:
                raise ValueError(f"{FIELDS[name][2]} must be on or off.")
        elif name in CLOCKS:
            if not isinstance(value, str) or not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", value):
                raise ValueError(f"{FIELDS[name][2]} must be a valid 24-hour time, such as 22:00.")
        elif name == "daily_goal_ml":
            if value is not None and (type(value) is not int or not 500 <= value <= 8000):
                raise ValueError("Daily goal must be a whole number from 500 to 8,000 ml, or automatic.")
        else:
            limit = 24 if name == "pet_name" else 48
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit or not value.isprintable():
                raise ValueError(f"{FIELDS[name][2]} must contain 1 to {limit} printable characters.")
            value = value.strip()
        clean[name] = value
    return clean


def settings_snapshot(data):
    return {name: data.get(section, {}).get(key) for name, (section, key, _) in FIELDS.items()}


def display_setting(name, value):
    if value is None:
        return "Automatic" if name == "daily_goal_ml" else "Not set"
    if type(value) is bool:
        return "On" if value else "Off"
    if name == "daily_goal_ml":
        return f"{value:,} ml"
    if name == "reminder_interval_minutes":
        return f"Every {value} minutes"
    if name == "units":
        return "US fl oz" if value == "oz" else "Millilitres"
    return str(value)


def apply_settings(data, store, changes, expected):
    """Merge into the latest saved account data, then update the session on success."""
    changes = validate_changes(changes)
    latest = store.load()
    current = settings_snapshot(latest)
    if any(current[name] != expected.get(name) for name in changes):
        raise ValueError("These settings changed since the preview. Ask FLOW again to prepare a fresh update.")
    candidate = deepcopy(latest)
    for name, value in changes.items():
        section, key, _ = FIELDS[name]
        candidate[section][key] = value
    if "pet_name" in changes:
        rename_pet(candidate, changes["pet_name"])
    if "daily_goal_ml" in changes:
        profile = candidate["profile"]
        target = changes["daily_goal_ml"]
        if target is None:
            target = calculate_goal(profile["age_group"], profile["occupation"], profile.get("custom_adjustment_ml", 0))
        set_daily_goal(candidate, target)
    if set(changes) & {"reminders_enabled", "reminder_interval_minutes", *CLOCKS}:
        preferences = candidate["preferences"]
        preferences["next_reminder_at"] = (
            (local_now() + timedelta(minutes=preferences["reminder_interval_minutes"])).isoformat(timespec="seconds")
            if preferences["reminders_enabled"] else None
        )
    store.save(candidate)
    data.clear()
    data.update(candidate)
    return "Saved: " + "; ".join(f"{FIELDS[name][2]} → {display_setting(name, value)}" for name, value in changes.items()) + "."
