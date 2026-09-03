"""Pure hydration calculations and state transitions for Water Buddy."""

from __future__ import annotations

import copy
import math
import uuid
from collections.abc import Mapping, MutableMapping
from datetime import date, datetime, time, timedelta
from typing import Any

from water_buddy.clock import local_now
from water_buddy.pet import (
    award_hydration_xp,
    default_pet_state,
    normalize_pet_state,
    revoke_hydration_xp,
)
from water_buddy.units import normalize_units

APP_ID = "water_buddy"
SCHEMA_VERSION = 4
WATER_LOG_COOLDOWN_SECONDS = 30
DEFAULT_QUICK_LOG_AMOUNTS_ML: tuple[int, int, int, int] = (250, 500, 750, 1000)
THEME_OPTIONS = ("Dark", "Light", "Japanese", "Cyber")

__all__ = (
    "AGE_GOALS",
    "APP_ID",
    "DEFAULT_QUICK_LOG_AMOUNTS_ML",
    "OCCUPATION_ADJUSTMENTS",
    "SCHEMA_VERSION",
    "THEME_OPTIONS",
    "WATER_LOG_COOLDOWN_SECONDS",
    "WaterLogCooldownError",
    "add_water",
    "badge_catalog",
    "calculate_goal",
    "calculate_streak",
    "calendar_week_rows",
    "default_state",
    "delete_water_entry",
    "dismiss_reminder",
    "ensure_today",
    "history_rows",
    "hydration_score",
    "normalize_state",
    "normalize_theme",
    "progress_summary",
    "reminder_is_due",
    "reset_day",
    "set_daily_goal",
    "snooze_reminder",
    "undo_last_water",
    "unlocked_badges",
    "update_water_entry",
    "validate_backup_payload",
    "water_log_cooldown_remaining",
)

AGE_GOALS: dict[str, int] = {
    "Children (4–8)": 1200,
    "Teens (9–13)": 1700,
    "Adults (14–64)": 2200,
    "Seniors (65+)": 1800,
}

OCCUPATION_ADJUSTMENTS: dict[str, int] = {
    "Athlete": 700,
    "Teacher": 200,
    "Office Worker": 0,
    "Outdoor Worker": 500,
    "Student": 150,
    "Custom": 0,
}


class WaterLogCooldownError(ValueError):
    """Report a blocked water log without exposing internal state details."""

    retry_after_seconds: int
    user_message: str

    def __init__(self, retry_after_seconds: int) -> None:
        """Create an error with a bounded, positive retry delay."""

        try:
            delay = math.ceil(float(retry_after_seconds))
        except (TypeError, ValueError, OverflowError):
            delay = 1
        self.retry_after_seconds = max(
            1,
            min(WATER_LOG_COOLDOWN_SECONDS, delay),
        )
        unit = "second" if self.retry_after_seconds == 1 else "seconds"
        self.user_message = (
            f"Please wait {self.retry_after_seconds} {unit} "
            "before logging another drink."
        )
        super().__init__(self.user_message)

_BADGE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "first_sip",
        "title": "First sip",
        "description": "Log water for the first time.",
        "icon": "water_drop",
        "accent": "#22D3EE",
    },
    {
        "id": "goal_getter",
        "title": "Goal getter",
        "description": "Reach your daily hydration goal.",
        "icon": "target",
        "accent": "#2DD4BF",
    },
    {
        "id": "three_day_streak",
        "title": "Making waves",
        "description": "Keep a three-day goal streak.",
        "icon": "waves",
        "accent": "#38BDF8",
    },
    {
        "id": "seven_day_streak",
        "title": "Week of wellness",
        "description": "Keep a seven-day goal streak.",
        "icon": "local_fire_department",
        "accent": "#818CF8",
    },
    {
        "id": "ten_litres",
        "title": "Ten-litre tide",
        "description": "Log 10 litres across your journey.",
        "icon": "tsunami",
        "accent": "#0EA5E9",
    },
    {
        "id": "twenty_litres",
        "title": "Twenty-litre tide",
        "description": "Log 20 litres across your journey.",
        "icon": "tsunami",
        "accent": "#0284C7",
    },
    {
        "id": "overachiever",
        "title": "Overflow energy",
        "description": "Go meaningfully beyond a daily goal.",
        "icon": "workspace_premium",
        "accent": "#F59E0B",
    },
    {
        "id": "thirty_day_streak",
        "title": "Hydration hero",
        "description": "Build a 30-day goal streak.",
        "icon": "workspace_premium",
        "accent": "#A78BFA",
    },
)

_BADGE_ALIASES: dict[str, str] = {
    "daily_goal": "goal_getter",
    "first_sip": "first_sip",
    "goal_getter": "goal_getter",
    "making_waves": "three_day_streak",
    "three_day_streak": "three_day_streak",
    "week_of_wellness": "seven_day_streak",
    "seven_day_streak": "seven_day_streak",
    "ten_liter_tide": "ten_litres",
    "ten_litre_tide": "ten_litres",
    "ten_litres": "ten_litres",
    "twenty_liter_tide": "twenty_litres",
    "twenty_litre_tide": "twenty_litres",
    "twenty_litres": "twenty_litres",
    "overflow_energy": "overachiever",
    "overachiever": "overachiever",
    "hydration_hero": "thirty_day_streak",
    "thirty_day_streak": "thirty_day_streak",
}


def _badge_identity(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get(
            "id",
            value.get("slug", value.get("title", value.get("name", ""))),
        )
    return (
        str(value or "")
        .strip()
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _canonical_badge_id(value: Any) -> str:
    identity = _badge_identity(value)
    return _BADGE_ALIASES.get(identity, identity)


def badge_catalog() -> list[dict[str, str]]:
    """Return an isolated copy of Water Buddy's authoritative badge catalog."""

    return copy.deepcopy(list(_BADGE_CATALOG))


def _normalize_quick_log_amounts(raw: Any) -> list[int]:
    values = raw if isinstance(raw, (list, tuple)) else ()
    normalized: list[int] = []
    for value in values:
        if isinstance(value, bool):
            continue
        try:
            numeric = float(value)
            amount = int(numeric)
        except (TypeError, ValueError, OverflowError):
            continue
        if not math.isfinite(numeric) or numeric != amount or not 1 <= amount <= 5000:
            continue
        if amount not in normalized:
            normalized.append(amount)
        if len(normalized) == 4:
            return normalized

    for amount in DEFAULT_QUICK_LOG_AMOUNTS_ML:
        if amount not in normalized:
            normalized.append(amount)
        if len(normalized) == 4:
            break
    return normalized


def _local_now(value: datetime | None = None) -> datetime:
    return local_now(value)


def _as_date(value: date | datetime | str | None = None) -> date:
    if value is None:
        return _local_now().date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return _local_now().date()


def _safe_int(
    value: Any,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        number = int(float(value))
    except (TypeError, ValueError, OverflowError):
        number = default
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _safe_bool(value: Any, default: bool) -> bool:
    """Return a persisted boolean without relying on container truthiness."""

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().casefold()
        if token in {"true", "1", "yes", "on", "enabled"}:
            return True
        if token in {"false", "0", "no", "off", "disabled"}:
            return False
    return default


def _clean_text(value: Any, fallback: str, max_length: int) -> str:
    text_value = str(value).strip() if value is not None else ""
    return (text_value or fallback)[:max_length]


def _canonical_choice(value: Any, choices: Mapping[str, int], fallback: str) -> str:
    candidate = str(value or "").strip()
    simplified = candidate.replace("-", "–").casefold()
    for choice in choices:
        if choice.casefold() == candidate.casefold() or choice.casefold() == simplified:
            return choice
    return fallback


def _valid_clock(value: Any, fallback: str) -> str:
    try:
        parsed = time.fromisoformat(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return parsed.strftime("%H:%M")


def _valid_iso_datetime(value: Any, fallback: datetime | None = None) -> str | None:
    if value in (None, ""):
        return fallback.isoformat(timespec="seconds") if fallback else None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return fallback.isoformat(timespec="seconds") if fallback else None
    return _local_now(parsed).isoformat(timespec="seconds")


def calculate_goal(
    age_group: str,
    occupation: str,
    custom_adjustment_ml: int = 0,
    manual_goal_ml: int | None = None,
) -> int:
    """Calculate a safe daily goal from age, occupation, and an override."""

    if manual_goal_ml is not None:
        return _safe_int(manual_goal_ml, 2200, minimum=500, maximum=8000)

    age_key = _canonical_choice(age_group, AGE_GOALS, "Adults (14–64)")
    occupation_key = _canonical_choice(
        occupation,
        OCCUPATION_ADJUSTMENTS,
        "Office Worker",
    )
    if occupation_key == "Custom":
        adjustment = _safe_int(
            custom_adjustment_ml,
            0,
            minimum=-500,
            maximum=3000,
        )
    else:
        adjustment = OCCUPATION_ADJUSTMENTS[occupation_key]
    return max(500, min(8000, AGE_GOALS[age_key] + adjustment))


def normalize_theme(value: object) -> str:
    """Return a supported display theme while preserving older profiles."""

    candidate = str(value).strip().casefold()
    return next(
        (theme for theme in THEME_OPTIONS if theme.casefold() == candidate),
        "Dark",
    )


def default_state(now: datetime | None = None) -> dict[str, Any]:
    """Return a new, fully initialized Water Buddy state dictionary."""

    current = _local_now(now)
    today_key = current.date().isoformat()
    goal_ml = AGE_GOALS["Adults (14–64)"]
    pet = default_pet_state(current)
    return {
        "profile": {
            "name": "Hydration hero",
            "age_group": "Adults (14–64)",
            "occupation": "Office Worker",
            "custom_adjustment_ml": 0,
            "manual_goal_ml": None,
            "wake_time": "07:00",
            "sleep_time": "22:00",
            "mascot_name": pet["name"],
            "pet": pet,
        },
        "preferences": {
            "theme": "Dark",
            "background_motion": True,
            "units": "ml",
            "quick_log_amounts_ml": list(DEFAULT_QUICK_LOG_AMOUNTS_ML),
            "reminders_enabled": True,
            "reminder_interval_minutes": 45,
            "quiet_start": "22:00",
            "quiet_end": "07:00",
            "sound_enabled": True,
            "interface_sound_volume": "Balanced",
            "next_reminder_at": (current + timedelta(minutes=45)).isoformat(
                timespec="seconds"
            ),
        },
        "daily_records": {
            today_key: {
                "goal_ml": goal_ml,
                "intake_ml": 0,
                "entries": [],
                "completed_at": None,
                "reset_count": 0,
            }
        },
        "achievements": [],
        "metadata": {
            "app_id": APP_ID,
            "schema_version": SCHEMA_VERSION,
            "created_at": current.isoformat(timespec="seconds"),
            "updated_at": current.isoformat(timespec="seconds"),
        },
    }


def _normalize_entry(raw: Any, record_date: date, index: int) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    amount_ml = _safe_int(raw.get("amount_ml", raw.get("amount", 0)), 0)
    if amount_ml <= 0 or amount_ml > 5000:
        return None
    fallback_time = datetime.combine(record_date, time(12, 0)) + timedelta(seconds=index)
    return {
        "id": _clean_text(raw.get("id"), uuid.uuid4().hex, 64),
        "amount_ml": amount_ml,
        "source": _clean_text(raw.get("source"), "Water", 64),
        "logged_at": _valid_iso_datetime(raw.get("logged_at"), fallback_time),
    }


def normalize_state(data: Any, now: datetime | None = None) -> dict[str, Any]:
    """Migrate and sanitize arbitrary persisted data into the current schema."""

    current = _local_now(now)
    defaults = default_state(current)
    if not isinstance(data, Mapping):
        return defaults

    raw_profile = data.get("profile", {})
    raw_profile = raw_profile if isinstance(raw_profile, Mapping) else {}
    age_group = _canonical_choice(
        raw_profile.get("age_group"), AGE_GOALS, "Adults (14–64)"
    )
    occupation = _canonical_choice(
        raw_profile.get("occupation"),
        OCCUPATION_ADJUSTMENTS,
        "Office Worker",
    )
    manual_raw = raw_profile.get("manual_goal_ml")
    manual_goal = (
        None
        if manual_raw in (None, "")
        else _safe_int(manual_raw, 2200, minimum=500, maximum=8000)
    )
    profile = dict(raw_profile)
    profile.update(
        {
            "name": _clean_text(raw_profile.get("name"), "Hydration hero", 48),
            "age_group": age_group,
            "occupation": occupation,
            "custom_adjustment_ml": _safe_int(
                raw_profile.get("custom_adjustment_ml"),
                0,
                minimum=-500,
                maximum=3000,
            ),
            "manual_goal_ml": manual_goal,
            "wake_time": _valid_clock(raw_profile.get("wake_time"), "07:00"),
            "sleep_time": _valid_clock(raw_profile.get("sleep_time"), "22:00"),
            "mascot_name": _clean_text(raw_profile.get("mascot_name"), "FLOW", 24),
        }
    )
    raw_pet = raw_profile.get("pet")
    if not isinstance(raw_pet, Mapping) and raw_profile.get("mascot_name"):
        # Preserve a mascot name from pre-pet Water Buddy profiles.
        raw_pet = {"name": raw_profile.get("mascot_name")}
    profile["pet"] = normalize_pet_state(raw_pet, current)
    profile["mascot_name"] = profile["pet"]["name"]

    raw_preferences = data.get("preferences", {})
    raw_preferences = raw_preferences if isinstance(raw_preferences, Mapping) else {}
    interval = _safe_int(
        raw_preferences.get("reminder_interval_minutes"),
        45,
        minimum=5,
        maximum=360,
    )
    reminders_enabled = _safe_bool(
        raw_preferences.get("reminders_enabled"),
        True,
    )
    next_default = current + timedelta(minutes=interval) if reminders_enabled else None
    preferences = dict(raw_preferences)
    raw_volume = str(
        raw_preferences.get("interface_sound_volume", "Balanced")
    ).strip().casefold()
    sound_volume = {
        "soft": "Soft",
        "balanced": "Balanced",
        "vivid": "Vivid",
    }.get(raw_volume, "Balanced")
    preferences.update(
        {
            "theme": normalize_theme(raw_preferences.get("theme", "Dark")),
            "background_motion": _safe_bool(
                raw_preferences.get("background_motion"),
                True,
            ),
            "units": (
                "oz"
                if normalize_units(raw_preferences.get("units", "ml")) == "oz"
                else "ml"
            ),
            "quick_log_amounts_ml": _normalize_quick_log_amounts(
                raw_preferences.get("quick_log_amounts_ml")
            ),
            "reminders_enabled": reminders_enabled,
            "reminder_interval_minutes": interval,
            "quiet_start": _valid_clock(raw_preferences.get("quiet_start"), "22:00"),
            "quiet_end": _valid_clock(raw_preferences.get("quiet_end"), "07:00"),
            "sound_enabled": _safe_bool(
                raw_preferences.get("sound_enabled"),
                True,
            ),
            "interface_sound_volume": sound_volume,
            "next_reminder_at": (
                _valid_iso_datetime(raw_preferences.get("next_reminder_at"), next_default)
                if reminders_enabled
                else None
            ),
        }
    )

    current_goal = calculate_goal(
        profile["age_group"],
        profile["occupation"],
        profile["custom_adjustment_ml"],
        profile["manual_goal_ml"],
    )
    raw_records = data.get("daily_records", {})
    raw_records = raw_records if isinstance(raw_records, Mapping) else {}
    records: dict[str, dict[str, Any]] = {}
    for raw_date, raw_record in raw_records.items():
        if not isinstance(raw_record, Mapping):
            continue
        try:
            record_date = date.fromisoformat(str(raw_date)[:10])
        except ValueError:
            continue
        raw_entries = raw_record.get("entries", [])
        entries: list[dict[str, Any]] = []
        entry_ids: set[str] = set()
        if isinstance(raw_entries, list):
            for index, raw_entry in enumerate(raw_entries):
                entry = _normalize_entry(raw_entry, record_date, index)
                if entry is not None:
                    if entry["id"] in entry_ids:
                        entry["id"] = uuid.uuid4().hex
                    entry_ids.add(entry["id"])
                    entries.append(entry)
        intake_default = sum(entry["amount_ml"] for entry in entries)
        intake_ml = _safe_int(
            raw_record.get("intake_ml", raw_record.get("intake", intake_default)),
            intake_default,
            minimum=0,
            maximum=100_000,
        )
        goal_ml = _safe_int(
            raw_record.get("goal_ml", raw_record.get("goal", current_goal)),
            current_goal,
            minimum=500,
            maximum=8000,
        )
        records[record_date.isoformat()] = {
            "goal_ml": goal_ml,
            "intake_ml": intake_ml,
            "entries": entries,
            "completed_at": (
                _valid_iso_datetime(raw_record.get("completed_at"))
                if intake_ml >= goal_ml
                else None
            ),
            "reset_count": _safe_int(
                raw_record.get("reset_count"), 0, minimum=0, maximum=1000
            ),
        }

    today_key = current.date().isoformat()
    if today_key not in records:
        legacy_intake = _safe_int(data.get("intake", 0), 0, minimum=0, maximum=100_000)
        legacy_goal = _safe_int(
            data.get("goal", current_goal), current_goal, minimum=500, maximum=8000
        )
        records[today_key] = {
            "goal_ml": legacy_goal,
            "intake_ml": legacy_intake,
            "entries": [],
            "completed_at": (
                current.isoformat(timespec="seconds")
                if legacy_intake >= legacy_goal
                else None
            ),
            "reset_count": 0,
        }

    raw_achievements = data.get("achievements", [])
    achievements: list[str] = []
    if isinstance(raw_achievements, list):
        for item in raw_achievements:
            badge_id = _canonical_badge_id(item)
            if badge_id and badge_id not in achievements:
                achievements.append(badge_id[:64])

    raw_metadata = data.get("metadata", {})
    raw_metadata = raw_metadata if isinstance(raw_metadata, Mapping) else {}
    created_at = _valid_iso_datetime(raw_metadata.get("created_at"), current)
    updated_at = _valid_iso_datetime(raw_metadata.get("updated_at"), current)
    metadata = dict(raw_metadata)
    metadata.update(
        {
            "app_id": APP_ID,
            "schema_version": SCHEMA_VERSION,
            "created_at": created_at,
            "updated_at": updated_at,
        }
    )

    return {
        "profile": profile,
        "preferences": preferences,
        "daily_records": records,
        "achievements": achievements,
        "metadata": metadata,
    }


def validate_backup_payload(
    raw: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate a Water Buddy backup envelope and return normalized state.

    Field-level damage is repaired by :func:`normalize_state`, but the outer
    document must be recognizably Water Buddy data. This prevents an unrelated
    JSON document from silently replacing a profile with defaults.
    """

    if not isinstance(raw, Mapping):
        raise ValueError("A Water Buddy backup must contain a JSON object.")

    expected_types: tuple[tuple[str, type[Any]], ...] = (
        ("profile", Mapping),
        ("preferences", Mapping),
        ("daily_records", Mapping),
        ("achievements", list),
        ("metadata", Mapping),
    )
    for key, expected_type in expected_types:
        if key in raw and not isinstance(raw[key], expected_type):
            raise ValueError(f"Water Buddy backup section {key!r} has the wrong type.")

    metadata = raw.get("metadata", {})
    metadata = metadata if isinstance(metadata, Mapping) else {}
    app_id = metadata.get("app_id")
    if app_id is not None and app_id != APP_ID:
        raise ValueError("This JSON document belongs to a different application.")

    raw_version = metadata.get("schema_version")
    version: int | None = None
    if raw_version is not None:
        if isinstance(raw_version, bool):
            raise ValueError("Water Buddy backup schema version is invalid.")
        try:
            numeric_version = float(raw_version)
            version = int(numeric_version)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Water Buddy backup schema version is invalid.") from error
        if (
            not math.isfinite(numeric_version)
            or numeric_version != version
            or not 1 <= version <= SCHEMA_VERSION
        ):
            raise ValueError("Water Buddy backup schema version is unsupported.")
        if version == SCHEMA_VERSION and app_id != APP_ID:
            raise ValueError("Water Buddy schema v4 backups must include the app ID.")

    core_sections = sum(
        isinstance(raw.get(key), Mapping)
        for key in ("profile", "preferences", "daily_records")
    )
    flat_legacy = "goal" in raw and "intake" in raw
    profile = raw.get("profile", {})
    preferences = raw.get("preferences", {})
    water_buddy_profile_keys = {
        "name",
        "age_group",
        "occupation",
        "custom_adjustment_ml",
        "manual_goal_ml",
        "wake_time",
        "sleep_time",
    }
    water_buddy_preference_keys = {
        "reminders_enabled",
        "reminder_interval_minutes",
        "quiet_start",
        "quiet_end",
        "theme",
        "units",
        "background_motion",
        "sound_enabled",
        "quick_log_amounts_ml",
    }
    structured_legacy = (
        isinstance(raw.get("daily_records"), Mapping)
        and (
            isinstance(profile, Mapping)
            and bool(water_buddy_profile_keys.intersection(profile))
            or isinstance(preferences, Mapping)
            and bool(water_buddy_preference_keys.intersection(preferences))
        )
    )
    identified_envelope = (
        core_sections >= 2 and (version is not None or app_id == APP_ID)
    )
    if not (flat_legacy or structured_legacy or identified_envelope):
        raise ValueError("This is not a recognized Water Buddy backup.")

    if flat_legacy:
        for key in ("goal", "intake"):
            value = raw[key]
            if isinstance(value, bool):
                raise ValueError("Legacy Water Buddy intake and goal must be numeric.")
            try:
                numeric = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(
                    "Legacy Water Buddy intake and goal must be numeric."
                ) from error
            if not math.isfinite(numeric):
                raise ValueError("Legacy Water Buddy intake and goal must be numeric.")

    return normalize_state(raw, now)


def ensure_today(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> dict[str, Any]:
    """Return today's record, creating a zero-intake record when needed."""

    target_date = _as_date(today)
    records = data.setdefault("daily_records", {})
    if not isinstance(records, dict):
        records = {}
        data["daily_records"] = records
    key = target_date.isoformat()
    record = records.get(key)
    if not isinstance(record, dict):
        profile = data.get("profile", {})
        profile = profile if isinstance(profile, Mapping) else {}
        goal_ml = calculate_goal(
            str(profile.get("age_group", "Adults (14–64)")),
            str(profile.get("occupation", "Office Worker")),
            _safe_int(profile.get("custom_adjustment_ml"), 0),
            profile.get("manual_goal_ml"),
        )
        record = {
            "goal_ml": goal_ml,
            "intake_ml": 0,
            "entries": [],
            "completed_at": None,
            "reset_count": 0,
        }
        records[key] = record
    record.setdefault("entries", [])
    record.setdefault("intake_ml", 0)
    record.setdefault("goal_ml", 2200)
    record.setdefault("completed_at", None)
    record.setdefault("reset_count", 0)
    return record


def _touch(data: MutableMapping[str, Any], now: datetime | None = None) -> None:
    metadata = data.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        data["metadata"] = metadata
    current = _local_now(now).isoformat(timespec="seconds")
    metadata.setdefault("created_at", current)
    metadata["updated_at"] = current
    metadata["app_id"] = APP_ID
    metadata["schema_version"] = SCHEMA_VERSION


def set_daily_goal(
    data: MutableMapping[str, Any],
    goal_ml: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Set today's canonical goal and reconcile its completion bookkeeping."""

    if isinstance(goal_ml, bool):
        raise ValueError(  # noqa: TRY004 - invalid user value, not a type contract
            "Daily goal must be a whole number of millilitres."
        )
    try:
        numeric = float(goal_ml)
        goal = int(numeric)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            "Daily goal must be a whole number of millilitres."
        ) from error
    if not math.isfinite(numeric) or numeric != goal:
        raise ValueError("Daily goal must be a whole number of millilitres.")
    if not 500 <= goal <= 8000:
        raise ValueError("Daily goal must be between 500 and 8,000 ml.")

    current = _local_now(now)
    record = ensure_today(data, current.date())
    intake = _safe_int(record.get("intake_ml"), 0, minimum=0)
    previous_goal = _safe_int(record.get("goal_ml"), 2200, minimum=1)
    previous_completion = _valid_iso_datetime(record.get("completed_at"))
    record["goal_ml"] = goal
    if intake >= goal:
        record["completed_at"] = (
            previous_completion
            if previous_goal == goal and previous_completion
            else current.isoformat(timespec="seconds")
        )
    else:
        record["completed_at"] = None

    _touch(data, current)
    _sync_achievements(data)
    return progress_summary(data, current.date(), current)


def _cooldown_entry_time(raw: Any, target_date: date) -> datetime | None:
    """Return a valid local timestamp for a cooldown-eligible entry."""

    if not isinstance(raw, Mapping):
        return None
    amount_raw = raw.get("amount_ml", raw.get("amount"))
    if isinstance(amount_raw, bool):
        return None
    try:
        amount_ml = int(amount_raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if not 1 <= amount_ml <= 5000:
        return None

    logged_at_raw = raw.get("logged_at")
    if logged_at_raw in (None, ""):
        return None
    try:
        logged_at = _local_now(datetime.fromisoformat(str(logged_at_raw).strip()))
    except (TypeError, ValueError):
        return None
    if logged_at.date() != target_date:
        return None
    return logged_at


def water_log_cooldown_remaining(
    data: Mapping[str, Any],
    now: datetime | None = None,
) -> int:
    """Return whole cooldown seconds left for today's newest valid water entry.

    The result is rounded upward and bounded from zero through
    ``WATER_LOG_COOLDOWN_SECONDS``. Invalid records, malformed entries, and entries
    whose timestamp belongs to another local day do not participate. Future
    timestamps are treated as a fresh entry, preventing clock skew from producing
    an unbounded retry value.
    """

    current = _local_now(now)
    if not isinstance(data, Mapping):
        return 0
    records = data.get("daily_records")
    if not isinstance(records, Mapping):
        return 0
    record = records.get(current.date().isoformat())
    if not isinstance(record, Mapping):
        return 0
    entries = record.get("entries")
    if not isinstance(entries, list):
        return 0

    latest: datetime | None = None
    for entry in entries:
        logged_at = _cooldown_entry_time(entry, current.date())
        if logged_at is not None and (latest is None or logged_at > latest):
            latest = logged_at
    if latest is None:
        return 0

    elapsed_seconds = max(0.0, (current - latest).total_seconds())
    if elapsed_seconds >= WATER_LOG_COOLDOWN_SECONDS:
        return 0
    remaining = math.ceil(WATER_LOG_COOLDOWN_SECONDS - elapsed_seconds)
    return max(1, min(WATER_LOG_COOLDOWN_SECONDS, remaining))


def _validated_water_amount(amount_ml: Any) -> int:
    if isinstance(amount_ml, bool):
        raise ValueError("Water amount must be a number of millilitres.")
    try:
        numeric = float(amount_ml)
        amount = int(numeric)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Water amount must be a whole number.") from error
    if not math.isfinite(numeric) or numeric != amount:
        raise ValueError("Water amount must be a whole number.")
    if not 1 <= amount <= 5000:
        raise ValueError("Water amount must be between 1 and 5,000 ml.")
    return amount


def add_water(
    data: MutableMapping[str, Any],
    amount_ml: int,
    source: str = "manual",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append a water entry and return the resulting daily summary."""

    amount = _validated_water_amount(amount_ml)

    current = _local_now(now)
    retry_after_seconds = water_log_cooldown_remaining(data, current)
    if retry_after_seconds > 0:
        raise WaterLogCooldownError(retry_after_seconds)

    record = ensure_today(data, current.date())
    before = int(record.get("intake_ml", 0))
    entry = {
        "id": uuid.uuid4().hex,
        "amount_ml": amount,
        "source": _clean_text(source, "Water", 64),
        "logged_at": current.isoformat(timespec="seconds"),
    }
    entries = record.setdefault("entries", [])
    if not isinstance(entries, list):
        entries = []
        record["entries"] = entries
    entries.append(entry)
    record["intake_ml"] = max(0, before + amount)
    award_hydration_xp(
        data,
        amount,
        event_id=entry["id"],
        now=current,
    )
    if before < int(record["goal_ml"]) <= int(record["intake_ml"]):
        record["completed_at"] = current.isoformat(timespec="seconds")
    _touch(data, current)
    _sync_achievements(data)
    return progress_summary(data, current.date(), current)


def update_water_entry(
    data: MutableMapping[str, Any],
    entry_id: str,
    amount_ml: int,
    source: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Edit today's entry by ID while preserving its identity and log time.

    A missing ID raises :class:`KeyError`; invalid amounts raise
    :class:`ValueError`. Pet rewards are reversed and re-awarded against the
    same event ID when the amount changes.
    """

    key = str(entry_id or "").strip()
    if not key:
        raise ValueError("Water entry ID cannot be blank.")
    amount = _validated_water_amount(amount_ml)
    current = _local_now(now)
    records = data.get("daily_records")
    record = (
        records.get(current.date().isoformat())
        if isinstance(records, MutableMapping)
        else None
    )
    entries = record.get("entries") if isinstance(record, MutableMapping) else None
    if not isinstance(entries, list):
        raise KeyError(key)

    entry: MutableMapping[str, Any] | None = None
    for candidate in entries:
        if isinstance(candidate, MutableMapping) and str(candidate.get("id", "")) == key:
            entry = candidate
            break
    if entry is None:
        raise KeyError(key)

    old_amount = _safe_int(entry.get("amount_ml"), 0, minimum=0, maximum=5000)
    old_source = str(entry.get("source", "Water"))
    new_source = old_source if source is None else _clean_text(source, "Water", 64)
    before_intake = _safe_int(record.get("intake_ml"), 0, minimum=0)
    changed = old_amount != amount or old_source != new_source

    if old_amount != amount:
        if old_amount > 0:
            revoke_hydration_xp(data, old_amount, event_id=key, now=current)
        entry["amount_ml"] = amount
        award_hydration_xp(data, amount, event_id=key, now=current)
        record["intake_ml"] = max(0, before_intake - old_amount + amount)
    if old_source != new_source:
        entry["source"] = new_source

    goal = _safe_int(record.get("goal_ml"), 2200, minimum=1)
    intake = _safe_int(record.get("intake_ml"), 0, minimum=0)
    previous_completion = record.get("completed_at")
    if intake >= goal:
        record["completed_at"] = previous_completion or current.isoformat(
            timespec="seconds"
        )
    else:
        record["completed_at"] = None
    changed = changed or record.get("completed_at") != previous_completion

    if changed:
        _touch(data, current)
        _sync_achievements(data)
    return progress_summary(data, current.date(), current)


def delete_water_entry(
    data: MutableMapping[str, Any],
    entry_id: str,
    now: datetime | None = None,
) -> bool:
    """Delete today's entry by stable ID, returning whether it was found."""

    key = str(entry_id or "").strip()
    if not key:
        return False
    current = _local_now(now)
    records = data.get("daily_records")
    record = (
        records.get(current.date().isoformat())
        if isinstance(records, MutableMapping)
        else None
    )
    entries = record.get("entries") if isinstance(record, MutableMapping) else None
    if not isinstance(entries, list):
        return False

    for index, candidate in enumerate(entries):
        if not isinstance(candidate, Mapping) or str(candidate.get("id", "")) != key:
            continue
        amount = _safe_int(candidate.get("amount_ml"), 0, minimum=0, maximum=5000)
        if amount > 0:
            revoke_hydration_xp(data, amount, event_id=key, now=current)
        del entries[index]
        record["intake_ml"] = max(
            0,
            _safe_int(record.get("intake_ml"), 0, minimum=0) - amount,
        )
        goal = _safe_int(record.get("goal_ml"), 2200, minimum=1)
        if _safe_int(record.get("intake_ml"), 0, minimum=0) < goal:
            record["completed_at"] = None
        _touch(data, current)
        _sync_achievements(data)
        return True
    return False


def undo_last_water(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> bool:
    """Remove today's newest logged entry, returning whether one existed."""

    record = ensure_today(data, today)
    entries = record.get("entries")
    if not isinstance(entries, list) or not entries:
        return False
    removed = entries.pop()
    amount = _safe_int(removed.get("amount_ml") if isinstance(removed, Mapping) else 0, 0)
    event_id = removed.get("id") if isinstance(removed, Mapping) else None
    if amount > 0:
        revoke_hydration_xp(data, amount, event_id=event_id)
    record["intake_ml"] = max(0, _safe_int(record.get("intake_ml"), 0) - amount)
    if int(record["intake_ml"]) < int(record.get("goal_ml", 2200)):
        record["completed_at"] = None
    _touch(data)
    return True


def reset_day(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> None:
    """Clear today's intake while preserving profile, settings, and history."""

    record = ensure_today(data, today)
    entries = record.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            amount = _safe_int(entry.get("amount_ml"), 0)
            if amount > 0:
                revoke_hydration_xp(
                    data,
                    amount,
                    event_id=entry.get("id"),
                )
    record["intake_ml"] = 0
    record["entries"] = []
    record["completed_at"] = None
    record["reset_count"] = _safe_int(record.get("reset_count"), 0) + 1
    _touch(data)


def progress_summary(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return normalized intake, goal, remaining volume, and feedback state."""

    target_date = _as_date(today if today is not None else (now.date() if now else None))
    record = ensure_today(data, target_date)
    intake_ml = _safe_int(record.get("intake_ml"), 0, minimum=0)
    goal_ml = _safe_int(record.get("goal_ml"), 2200, minimum=1)
    progress = intake_ml / goal_ml
    percentage = progress * 100
    if progress >= 1:
        status, message = "goal_achieved", "Goal achieved — excellent work!"
    elif progress >= 0.75:
        status, message = "almost_there", "Almost there — keep the steady rhythm."
    elif progress >= 0.5:
        status, message = "in_the_flow", "Nice work — you are over halfway there."
    elif progress >= 0.25:
        status, message = "building_momentum", "Good start — keep your bottle nearby."
    elif progress > 0:
        status, message = "getting_started", "Every sip builds momentum."
    else:
        status, message = "ready", "Your first sip is ready when you are."
    entries = record.get("entries", [])
    return {
        "date": target_date.isoformat(),
        "intake_ml": intake_ml,
        "goal_ml": goal_ml,
        "remaining_ml": max(0, goal_ml - intake_ml),
        "progress": progress,
        "percentage": percentage,
        "goal_met": intake_ml >= goal_ml,
        "status": status,
        "message": message,
        "entries": copy.deepcopy(entries if isinstance(entries, list) else []),
        "completed_at": record.get("completed_at"),
    }


def history_rows(
    data: MutableMapping[str, Any],
    days: int = 7,
    today: date | datetime | str | None = None,
) -> list[dict[str, Any]]:
    """Return an oldest-first, gap-filled daily history window."""

    window = _safe_int(days, 7, minimum=1, maximum=366)
    end_date = _as_date(today)
    profile = data.get("profile", {})
    profile = profile if isinstance(profile, Mapping) else {}
    fallback_goal = calculate_goal(
        str(profile.get("age_group", "Adults (14–64)")),
        str(profile.get("occupation", "Office Worker")),
        _safe_int(profile.get("custom_adjustment_ml"), 0),
        profile.get("manual_goal_ml"),
    )
    records = data.get("daily_records", {})
    records = records if isinstance(records, Mapping) else {}
    rows: list[dict[str, Any]] = []
    for offset in range(window - 1, -1, -1):
        day = end_date - timedelta(days=offset)
        raw = records.get(day.isoformat(), {})
        raw = raw if isinstance(raw, Mapping) else {}
        intake_ml = _safe_int(raw.get("intake_ml"), 0, minimum=0)
        goal_ml = _safe_int(raw.get("goal_ml"), fallback_goal, minimum=1)
        progress = intake_ml / goal_ml
        entries = raw.get("entries", [])
        rows.append(
            {
                "date": day.isoformat(),
                "day": day.strftime("%a"),
                "intake_ml": intake_ml,
                "goal_ml": goal_ml,
                "progress": progress,
                "percentage": progress * 100,
                "goal_met": intake_ml >= goal_ml,
                "entries_count": len(entries) if isinstance(entries, list) else 0,
            }
        )
    return rows


def calendar_week_rows(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> list[dict[str, Any]]:
    """Return Monday-through-Sunday rows for the week containing ``today``."""

    current_day = _as_date(today)
    week_end = current_day + timedelta(days=6 - current_day.weekday())
    return history_rows(data, days=7, today=week_end)


def calculate_streak(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> int:
    """Return consecutive goal days, without penalizing an unfinished today."""

    current_day = _as_date(today)
    records = data.get("daily_records", {})
    records = records if isinstance(records, Mapping) else {}

    today_record = records.get(current_day.isoformat(), {})
    today_record = today_record if isinstance(today_record, Mapping) else {}
    today_met = _safe_int(today_record.get("intake_ml"), 0) >= _safe_int(
        today_record.get("goal_ml"), 2200, minimum=1
    )
    cursor = current_day if today_met else current_day - timedelta(days=1)
    streak = 0
    while True:
        record = records.get(cursor.isoformat())
        if not isinstance(record, Mapping):
            break
        intake = _safe_int(record.get("intake_ml"), 0, minimum=0)
        goal = _safe_int(record.get("goal_ml"), 2200, minimum=1)
        if intake < goal:
            break
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _longest_streak(data: Mapping[str, Any]) -> int:
    records = data.get("daily_records", {})
    if not isinstance(records, Mapping):
        return 0
    parsed: list[tuple[date, bool]] = []
    for key, record in records.items():
        if not isinstance(record, Mapping):
            continue
        try:
            day = date.fromisoformat(str(key)[:10])
        except ValueError:
            continue
        met = _safe_int(record.get("intake_ml"), 0) >= _safe_int(
            record.get("goal_ml"), 2200, minimum=1
        )
        parsed.append((day, met))
    parsed.sort()
    longest = running = 0
    previous: date | None = None
    for day, met in parsed:
        if met and previous is not None and day == previous + timedelta(days=1):
            running += 1
        elif met:
            running = 1
        else:
            running = 0
        longest = max(longest, running)
        previous = day
    return longest


def _derived_badge_ids(data: Mapping[str, Any]) -> set[str]:
    records = data.get("daily_records", {})
    records = records if isinstance(records, Mapping) else {}
    total_intake = 0
    goal_days = 0
    has_overachieved = False
    for record in records.values():
        if not isinstance(record, Mapping):
            continue
        intake = _safe_int(record.get("intake_ml"), 0, minimum=0)
        goal = _safe_int(record.get("goal_ml"), 2200, minimum=1)
        total_intake += intake
        goal_days += int(intake >= goal)
        has_overachieved = has_overachieved or intake >= goal * 1.25
    longest = _longest_streak(data)
    unlocked: set[str] = set()
    if total_intake > 0:
        unlocked.add("first_sip")
    if goal_days:
        unlocked.add("goal_getter")
    if longest >= 3:
        unlocked.add("three_day_streak")
    if longest >= 7:
        unlocked.add("seven_day_streak")
    if total_intake >= 10_000:
        unlocked.add("ten_litres")
    if total_intake >= 20_000:
        unlocked.add("twenty_litres")
    if has_overachieved:
        unlocked.add("overachiever")
    if longest >= 30:
        unlocked.add("thirty_day_streak")
    return unlocked


def _sync_achievements(data: MutableMapping[str, Any]) -> None:
    existing = data.setdefault("achievements", [])
    if not isinstance(existing, list):
        existing = []
        data["achievements"] = existing
    normalized_existing: list[str] = []
    for item in existing:
        badge_id = _canonical_badge_id(item)
        if badge_id and badge_id not in normalized_existing:
            normalized_existing.append(badge_id)
    if normalized_existing != existing:
        existing[:] = normalized_existing
    existing_ids = set(normalized_existing)
    derived = _derived_badge_ids(data)
    for badge in _BADGE_CATALOG:
        if badge["id"] in derived and badge["id"] not in existing_ids:
            existing.append(badge["id"])


def unlocked_badges(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> list[dict[str, str]]:
    """Return badge metadata for every durable or currently earned badge."""

    del today  # Badges are lifetime achievements, not limited to one day.
    existing = data.get("achievements", [])
    existing_ids = {
        _canonical_badge_id(item)
        for item in (existing if isinstance(existing, list) else [])
    }
    earned = existing_ids | _derived_badge_ids(data)
    return [badge for badge in badge_catalog() if badge["id"] in earned]


def hydration_score(
    data: MutableMapping[str, Any],
    today: date | datetime | str | None = None,
) -> int:
    """Return a 0-100 score across up to seven account-eligible days."""

    end_date = _as_date(today)
    metadata = data.get("metadata", {})
    metadata = metadata if isinstance(metadata, Mapping) else {}
    try:
        eligible_start = datetime.fromisoformat(str(metadata["created_at"])).date()
    except (KeyError, TypeError, ValueError):
        records = data.get("daily_records", {})
        record_dates: list[date] = []
        if isinstance(records, Mapping):
            for key in records:
                try:
                    record_dates.append(date.fromisoformat(str(key)[:10]))
                except ValueError:
                    continue
        eligible_start = min(record_dates, default=end_date)
    eligible_start = max(eligible_start, end_date - timedelta(days=6))
    eligible_start = min(eligible_start, end_date)
    eligible_days = (end_date - eligible_start).days + 1
    rows = history_rows(data, days=eligible_days, today=end_date)
    if not any(row["intake_ml"] > 0 for row in rows):
        return 0
    adherence = sum(min(1.0, float(row["progress"])) for row in rows) / eligible_days
    goal_days = sum(bool(row["goal_met"]) for row in rows)
    streak = calculate_streak(data, end_date)
    score = (
        adherence * 65
        + (goal_days / eligible_days) * 20
        + min(streak / eligible_days, 1) * 15
    )
    return max(0, min(100, round(score)))


def _clock_minutes(value: Any, fallback: str) -> int:
    clock = _valid_clock(value, fallback)
    parsed = time.fromisoformat(clock)
    return parsed.hour * 60 + parsed.minute


def _inside_window(moment_minutes: int, start_minutes: int, end_minutes: int) -> bool:
    if start_minutes == end_minutes:
        return True
    if start_minutes < end_minutes:
        return start_minutes <= moment_minutes < end_minutes
    return moment_minutes >= start_minutes or moment_minutes < end_minutes


def reminder_is_due(
    data: MutableMapping[str, Any],
    now: datetime | None = None,
) -> bool:
    """Return whether an enabled reminder is due within active, non-quiet hours."""

    current = _local_now(now)
    preferences = data.get("preferences", {})
    preferences = preferences if isinstance(preferences, MutableMapping) else {}
    if not bool(preferences.get("reminders_enabled", True)):
        return False

    records = data.get("daily_records", {})
    record = (
        records.get(current.date().isoformat())
        if isinstance(records, Mapping)
        else None
    )
    if isinstance(record, Mapping):
        intake = _safe_int(record.get("intake_ml"), 0, minimum=0)
        goal = _safe_int(record.get("goal_ml"), 2200, minimum=1)
        if intake >= goal:
            return False

    profile = data.get("profile", {})
    profile = profile if isinstance(profile, Mapping) else {}
    minute = current.hour * 60 + current.minute
    wake = _clock_minutes(profile.get("wake_time"), "07:00")
    sleep = _clock_minutes(profile.get("sleep_time"), "22:00")
    quiet_start = _clock_minutes(preferences.get("quiet_start"), "22:00")
    quiet_end = _clock_minutes(preferences.get("quiet_end"), "07:00")
    if not _inside_window(minute, wake, sleep):
        return False
    if _inside_window(minute, quiet_start, quiet_end):
        return False

    scheduled_raw = preferences.get("next_reminder_at")
    if not scheduled_raw:
        interval = _safe_int(
            preferences.get("reminder_interval_minutes"), 45, minimum=5, maximum=360
        )
        if isinstance(preferences, MutableMapping):
            preferences["next_reminder_at"] = (
                current + timedelta(minutes=interval)
            ).isoformat(timespec="seconds")
        return False
    try:
        scheduled = _local_now(datetime.fromisoformat(str(scheduled_raw)))
    except (TypeError, ValueError):
        return False
    return current >= scheduled


def snooze_reminder(
    data: MutableMapping[str, Any],
    minutes: int = 10,
    now: datetime | None = None,
) -> None:
    """Move the next reminder a bounded number of minutes into the future."""

    delay = _safe_int(minutes, 10, minimum=1, maximum=180)
    current = _local_now(now)
    preferences = data.setdefault("preferences", {})
    if not isinstance(preferences, dict):
        preferences = {}
        data["preferences"] = preferences
    preferences["next_reminder_at"] = (current + timedelta(minutes=delay)).isoformat(
        timespec="seconds"
    )
    _touch(data, current)


def dismiss_reminder(
    data: MutableMapping[str, Any],
    now: datetime | None = None,
) -> None:
    """Schedule the next reminder from now using the configured interval."""

    current = _local_now(now)
    preferences = data.setdefault("preferences", {})
    if not isinstance(preferences, dict):
        preferences = {}
        data["preferences"] = preferences
    if not bool(preferences.get("reminders_enabled", True)):
        preferences["next_reminder_at"] = None
    else:
        interval = _safe_int(
            preferences.get("reminder_interval_minutes"), 45, minimum=5, maximum=360
        )
        preferences["next_reminder_at"] = (
            current + timedelta(minutes=interval)
        ).isoformat(timespec="seconds")
    preferences["last_reminder_dismissed_at"] = current.isoformat(timespec="seconds")
    _touch(data, current)
