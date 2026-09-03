"""Standalone hydration-pet state and progression for Water Buddy.

The module deliberately has no dependency on :mod:`water_buddy.domain`. Pet
state is stored below ``data["profile"]["pet"]`` so existing Water Buddy JSON
normalization preserves it without creating an import cycle.
"""

from __future__ import annotations

import copy
import math
from bisect import bisect_right
from collections.abc import Mapping, MutableMapping
from datetime import date, datetime, timedelta
from typing import Any

from water_buddy.clock import local_now

PET_SCHEMA_VERSION = 1
DEFAULT_PET_NAME = "Ripple"
PET_SPECIES = "Aqualing"

LEVEL_XP_THRESHOLDS: tuple[int, ...] = (
    0,
    40,
    100,
    180,
    280,
    400,
    550,
    730,
    940,
    1180,
    1450,
    1750,
    2080,
    2440,
    2830,
    3250,
    3700,
    4180,
    4690,
    5230,
)
MAX_LEVEL = len(LEVEL_XP_THRESHOLDS)

EVOLUTION_STAGES: tuple[dict[str, Any], ...] = (
    {"id": "dewdrop", "name": "Dewdrop", "min_level": 1},
    {"id": "rippleling", "name": "Rippleling", "min_level": 3},
    {"id": "tidekin", "name": "Tidekin", "min_level": 6},
    {"id": "aqualume", "name": "Aqualume", "min_level": 9},
)

ACCESSORIES: dict[str, dict[str, Any]] = {
    "none": {"id": "none", "name": "No accessory", "icon": "block", "min_level": 1},
    "seafoam_bow": {
        "id": "seafoam_bow",
        "name": "Seafoam bow",
        "icon": "ribbon",
        "min_level": 2,
    },
    "sunny_visor": {
        "id": "sunny_visor",
        "name": "Sunny visor",
        "icon": "eyeglasses",
        "min_level": 4,
    },
    "coral_crown": {
        "id": "coral_crown",
        "name": "Coral crown",
        "icon": "crown",
        "min_level": 7,
    },
    "star_shell": {
        "id": "star_shell",
        "name": "Star shell",
        "icon": "star",
        "min_level": 10,
    },
    "samurai_fit": {
        "id": "samurai_fit",
        "name": "Samurai fit",
        "icon": "swords",
        "min_level": 10,
    },
    "cyborg_fit": {
        "id": "cyborg_fit",
        "name": "Cyborg fit",
        "icon": "memory",
        "min_level": 15,
    },
    "cool_guy_fit": {
        "id": "cool_guy_fit",
        "name": "Cool guy fit",
        "icon": "mode_cool",
        "min_level": 20,
    },
}

CARE_ACTIONS: dict[str, dict[str, Any]] = {
    "play": {
        "name": "Play",
        "energy": -6.0,
        "happiness": 14.0,
        "xp": 5,
        "cooldown_minutes": 45,
        "daily_limit": 4,
    },
    "rest": {
        "name": "Rest",
        "energy": 18.0,
        "happiness": 2.0,
        "xp": 3,
        "cooldown_minutes": 90,
        "daily_limit": 3,
    },
    "encourage": {
        "name": "Encourage",
        "energy": 3.0,
        "happiness": 8.0,
        "xp": 3,
        "cooldown_minutes": 30,
        "daily_limit": 5,
    },
}

DAILY_HYDRATION_XP_CAP = 80
MAX_REWARDED_EVENTS = 500
DECAY_GRACE_HOURS = 1.0
ENERGY_DECAY_PER_HOUR = 0.75
HAPPINESS_DECAY_PER_HOUR = 0.40
MAX_DECAY_HOURS = 72.0

HOURLY_PET_QUOTES: tuple[str, ...] = (
    "Small sips can build steady habits.",
    "Every refill is a fresh little start.",
    "Consistency turns tiny ripples into a flowing routine.",
    "Keep it gentle, keep it steady, keep it flowing.",
    "Your next healthy choice can be wonderfully small.",
    "A bottle nearby is a quiet promise to your future self.",
    "Progress is made one mindful sip at a time.",
    "There is no race here—just a rhythm that works for you.",
)

HOURLY_PET_TIPS: tuple[str, ...] = (
    "Keep a reusable bottle where you can easily see and reach it.",
    "Serve water with meals to make it part of an existing routine.",
    "Add lemon, lime, cucumber, or berries when you want more flavor.",
    "Choose water instead of a sugary drink when that suits you.",
    "Use a regular daily cue—like a break or meal—as a refill reminder.",
    "Choose water when eating out for a simple hydration-friendly option.",
    "Hot weather and physical activity can increase your fluid needs.",
    "Water-rich fruits and vegetables can also contribute to fluid intake.",
)

HOURLY_PET_FACTS: tuple[str, ...] = (
    "Water helps your body maintain a normal temperature.",
    "Water helps lubricate and cushion your joints.",
    "Water helps protect the spinal cord and other sensitive tissues.",
    "Your body uses water to remove waste through several normal processes.",
    "Food—especially many fruits and vegetables—can add to fluid intake.",
    "Hydration needs vary with factors such as age, activity, and environment.",
    "Plain water has no calories.",
    "Dehydration can affect clear thinking and mood and can contribute to overheating.",
)


def _local_now(value: datetime | None = None) -> datetime:
    return local_now(value)


def hourly_pet_message(now: datetime | None = None) -> dict[str, str]:
    """Return a stable quote, tip, or fact for the current local hour.

    The hour itself selects the content, so the message advances without
    writing timer state and immediately catches up after the app is reopened.
    """

    current = _local_now(now)
    absolute_hour = current.date().toordinal() * 24 + current.hour
    catalogs = (
        ("Quote", HOURLY_PET_QUOTES),
        ("Tip", HOURLY_PET_TIPS),
        ("Fact", HOURLY_PET_FACTS),
    )
    kind, messages = catalogs[absolute_hour % len(catalogs)]
    message_index = (absolute_hour // len(catalogs)) % len(messages)
    return {
        "kind": kind,
        "text": messages[message_index],
        "hour_key": current.strftime("%Y-%m-%dT%H"),
    }


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
        result = int(float(value))
    except (TypeError, ValueError, OverflowError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _safe_float(
    value: Any,
    default: float,
    *,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    try:
        if isinstance(value, bool):
            raise ValueError
        result = float(value)
        if not math.isfinite(result):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        result = default
    return max(minimum, min(maximum, result))


def _clean_name(value: Any, fallback: str = DEFAULT_PET_NAME) -> str:
    candidate = " ".join(str(value or "").split())
    candidate = "".join(character for character in candidate if character.isprintable())
    return (candidate or fallback)[:24]


def _accessory_id(value: Any) -> str:
    """Return the canonical persisted identifier for an accessory value."""

    return "_".join(
        str(value or "none")
        .casefold()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def _valid_moment(value: Any, fallback: datetime) -> str:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        parsed = fallback
    return _local_now(parsed).isoformat(timespec="seconds")


def _level_for_xp(xp: int) -> int:
    return min(MAX_LEVEL, max(1, bisect_right(LEVEL_XP_THRESHOLDS, max(0, xp))))


def _stage_for_level(level: int) -> dict[str, Any]:
    stage = EVOLUTION_STAGES[0]
    for candidate in EVOLUTION_STAGES:
        if level < int(candidate["min_level"]):
            break
        stage = candidate
    return copy.deepcopy(stage)


def _sync_progress(pet: MutableMapping[str, Any]) -> None:
    xp = _safe_int(pet.get("xp"), 0, minimum=0, maximum=1_000_000)
    level = _level_for_xp(xp)
    pet["xp"] = xp
    pet["level"] = level
    pet["evolution_stage"] = _stage_for_level(level)["id"]
    unlocked = [
        accessory_id
        for accessory_id, accessory in ACCESSORIES.items()
        if level >= int(accessory["min_level"])
    ]
    if pet.get("equipped_accessory") not in unlocked:
        pet["equipped_accessory"] = "none"


def _default_daily_activity(today: date) -> dict[str, Any]:
    return {
        "date": today.isoformat(),
        "hydration_ml": 0,
        "hydration_events": 0,
        "care_actions": 0,
        "xp_earned": 0,
        "hydration_xp": 0,
    }


def default_pet_state(now: datetime | None = None) -> dict[str, Any]:
    """Return a new Aqualing companion with safe, fully populated state."""

    current = _local_now(now)
    timestamp = current.isoformat(timespec="seconds")
    return {
        "schema_version": PET_SCHEMA_VERSION,
        "name": DEFAULT_PET_NAME,
        "species": PET_SPECIES,
        "xp": 0,
        "level": 1,
        "evolution_stage": "dewdrop",
        "energy": 86.0,
        "happiness": 84.0,
        "equipped_accessory": "none",
        "created_at": timestamp,
        "last_updated_at": timestamp,
        "rewarded_events": {},
        "care": {"last_actions": {}, "daily_counts": {}},
        "daily_activity": _default_daily_activity(current.date()),
    }


def normalize_pet_state(raw: Any, now: datetime | None = None) -> dict[str, Any]:
    """Sanitize arbitrary persisted input into the current pet schema."""

    current = _local_now(now)
    defaults = default_pet_state(current)
    if not isinstance(raw, Mapping):
        return defaults

    xp = _safe_int(raw.get("xp"), 0, minimum=0, maximum=1_000_000)
    level = _level_for_xp(xp)
    created_at = _valid_moment(raw.get("created_at"), current)
    last_updated_at = _valid_moment(raw.get("last_updated_at"), current)

    raw_events = raw.get("rewarded_events", {})
    events: dict[str, dict[str, Any]] = {}
    if isinstance(raw_events, Mapping):
        ordered_events = list(raw_events.items())[-MAX_REWARDED_EVENTS:]
        for raw_id, raw_event in ordered_events:
            if not isinstance(raw_event, Mapping):
                continue
            event_id = str(raw_id).strip()[:128]
            amount = _safe_int(raw_event.get("amount_ml"), 0, minimum=0, maximum=5000)
            if not event_id or amount <= 0:
                continue
            events[event_id] = {
                "amount_ml": amount,
                "xp": _safe_int(raw_event.get("xp"), 0, minimum=0, maximum=50),
                "energy_boost": _safe_float(raw_event.get("energy_boost"), 0, maximum=20),
                "happiness_boost": _safe_float(
                    raw_event.get("happiness_boost"), 0, maximum=20
                ),
                "awarded_at": _valid_moment(raw_event.get("awarded_at"), current),
            }

    raw_care = raw.get("care", {})
    raw_care = raw_care if isinstance(raw_care, Mapping) else {}
    raw_last_actions = raw_care.get("last_actions", {})
    last_actions: dict[str, str] = {}
    if isinstance(raw_last_actions, Mapping):
        for action in CARE_ACTIONS:
            if raw_last_actions.get(action):
                last_actions[action] = _valid_moment(raw_last_actions[action], current)
    raw_daily_counts = raw_care.get("daily_counts", {})
    daily_counts: dict[str, dict[str, int]] = {}
    if isinstance(raw_daily_counts, Mapping):
        for raw_day, counts in list(raw_daily_counts.items())[-14:]:
            try:
                day_key = date.fromisoformat(str(raw_day)[:10]).isoformat()
            except ValueError:
                continue
            if not isinstance(counts, Mapping):
                continue
            daily_counts[day_key] = {
                action: _safe_int(counts.get(action), 0, minimum=0, maximum=100)
                for action in CARE_ACTIONS
            }

    raw_activity = raw.get("daily_activity", {})
    raw_activity = raw_activity if isinstance(raw_activity, Mapping) else {}
    try:
        activity_date = date.fromisoformat(str(raw_activity.get("date"))[:10])
    except (TypeError, ValueError):
        activity_date = current.date()
    activity = {
        "date": activity_date.isoformat(),
        "hydration_ml": _safe_int(
            raw_activity.get("hydration_ml"), 0, minimum=0, maximum=100_000
        ),
        "hydration_events": _safe_int(
            raw_activity.get("hydration_events"), 0, minimum=0, maximum=1000
        ),
        "care_actions": _safe_int(
            raw_activity.get("care_actions"), 0, minimum=0, maximum=1000
        ),
        "xp_earned": _safe_int(
            raw_activity.get("xp_earned"), 0, minimum=0, maximum=10_000
        ),
        "hydration_xp": _safe_int(
            raw_activity.get("hydration_xp"), 0, minimum=0, maximum=DAILY_HYDRATION_XP_CAP
        ),
    }

    state = {
        "schema_version": PET_SCHEMA_VERSION,
        "name": _clean_name(raw.get("name")),
        "species": PET_SPECIES,
        "xp": xp,
        "level": level,
        "evolution_stage": _stage_for_level(level)["id"],
        "energy": _safe_float(raw.get("energy"), defaults["energy"]),
        "happiness": _safe_float(raw.get("happiness"), defaults["happiness"]),
        "equipped_accessory": _accessory_id(raw.get("equipped_accessory", "none")),
        "created_at": created_at,
        "last_updated_at": last_updated_at,
        "rewarded_events": events,
        "care": {"last_actions": last_actions, "daily_counts": daily_counts},
        "daily_activity": activity,
    }
    _sync_progress(state)
    return state


def _raw_pet(data: Mapping[str, Any]) -> Any:
    profile = data.get("profile", {})
    return profile.get("pet") if isinstance(profile, Mapping) else None


def _store_pet(data: MutableMapping[str, Any], pet: dict[str, Any]) -> None:
    profile = data.setdefault("profile", {})
    if not isinstance(profile, dict):
        profile = {}
        data["profile"] = profile
    profile["pet"] = pet


def _decayed_state(pet: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    state = normalize_pet_state(pet, now)
    try:
        previous = _local_now(datetime.fromisoformat(str(state["last_updated_at"])))
    except (TypeError, ValueError):
        previous = now
    elapsed_hours = max(0.0, (now - previous).total_seconds() / 3600)
    decay_hours = min(MAX_DECAY_HOURS, max(0.0, elapsed_hours - DECAY_GRACE_HOURS))
    state["energy"] = round(
        max(0.0, float(state["energy"]) - decay_hours * ENERGY_DECAY_PER_HOUR), 2
    )
    state["happiness"] = round(
        max(0.0, float(state["happiness"]) - decay_hours * HAPPINESS_DECAY_PER_HOUR), 2
    )
    return state


def _roll_daily_activity(pet: MutableMapping[str, Any], today: date) -> dict[str, Any]:
    activity = pet.get("daily_activity")
    if not isinstance(activity, dict) or activity.get("date") != today.isoformat():
        activity = _default_daily_activity(today)
        pet["daily_activity"] = activity
    return activity


def _decorate_snapshot(pet: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    snapshot = copy.deepcopy(dict(pet))
    level = int(snapshot["level"])
    xp = int(snapshot["xp"])
    current_threshold = LEVEL_XP_THRESHOLDS[level - 1]
    if level < MAX_LEVEL:
        next_threshold = LEVEL_XP_THRESHOLDS[level]
        xp_to_next = next_threshold - xp
        level_progress = (xp - current_threshold) / (next_threshold - current_threshold)
    else:
        next_threshold = current_threshold
        xp_to_next = 0
        level_progress = 1.0
    stage = _stage_for_level(level)
    next_stage = next(
        (copy.deepcopy(item) for item in EVOLUTION_STAGES if int(item["min_level"]) > level),
        None,
    )
    unlocked = [
        accessory_id
        for accessory_id, accessory in ACCESSORIES.items()
        if level >= int(accessory["min_level"])
    ]
    available = []
    for accessory in ACCESSORIES.values():
        item = copy.deepcopy(accessory)
        item["unlocked"] = item["id"] in unlocked
        item["equipped"] = item["id"] == snapshot["equipped_accessory"]
        available.append(item)
    energy = float(snapshot["energy"])
    happiness = float(snapshot["happiness"])
    if min(energy, happiness) < 20:
        mood = "sleepy"
    elif happiness < 35:
        mood = "lonely"
    elif energy < 35:
        mood = "tired"
    elif (energy + happiness) / 2 >= 80:
        mood = "sparkling"
    elif (energy + happiness) / 2 >= 60:
        mood = "happy"
    else:
        mood = "calm"
    snapshot.update(
        {
            "stage": stage,
            "evolution_name": stage["name"],
            "next_evolution": next_stage,
            "xp_into_level": xp - current_threshold,
            "xp_for_next_level": max(0, next_threshold - current_threshold),
            "xp_to_next_level": max(0, xp_to_next),
            "level_progress": max(0.0, min(1.0, level_progress)),
            "is_max_level": level == MAX_LEVEL,
            "mood": mood,
            "unlocked_accessories": unlocked,
            "available_accessories": available,
            "snapshot_at": now.isoformat(timespec="seconds"),
        }
    )
    return snapshot


def pet_snapshot(data: Mapping[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Return a read-only, naturally decayed and fully derived pet snapshot."""

    if not isinstance(data, Mapping):
        raise TypeError("Water Buddy data must be a mapping.")
    current = _local_now(now)
    pet = _decayed_state(_raw_pet(data), current)
    return _decorate_snapshot(pet, current)


def _prepare_mutation(
    data: MutableMapping[str, Any], now: datetime
) -> dict[str, Any]:
    if not isinstance(data, MutableMapping):
        raise TypeError("Water Buddy data must be mutable.")
    pet = _decayed_state(_raw_pet(data), now)
    _roll_daily_activity(pet, now.date())
    _store_pet(data, pet)
    return pet


def _finish_mutation(pet: MutableMapping[str, Any], now: datetime) -> None:
    _sync_progress(pet)
    pet["last_updated_at"] = now.isoformat(timespec="seconds")


def _validate_amount(amount_ml: int) -> int:
    if isinstance(amount_ml, bool):
        raise ValueError("Hydration amount must be a whole number of millilitres.")
    try:
        amount = int(amount_ml)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Hydration amount must be a whole number of millilitres.") from error
    if not 1 <= amount <= 5000:
        raise ValueError("Hydration amount must be between 1 and 5,000 ml.")
    return amount


def award_hydration_xp(
    data: MutableMapping[str, Any],
    amount_ml: int,
    event_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Reward one water event exactly once and return the award result."""

    amount = _validate_amount(amount_ml)
    current = _local_now(now)
    pet = _prepare_mutation(data, current)
    pet_name = str(pet.get("name", DEFAULT_PET_NAME))
    events = pet["rewarded_events"]
    key = str(event_id or f"auto:{current.isoformat(timespec='seconds')}:{amount}").strip()[:128]
    if not key:
        raise ValueError("Event ID cannot be blank.")
    if key in events:
        return {
            "awarded": False,
            "reason": "duplicate_event",
            "message": f"This hydration event already rewarded {pet_name}.",
            "xp_awarded": 0,
            "event_id": key,
            "snapshot": _decorate_snapshot(pet, current),
        }

    activity = _roll_daily_activity(pet, current.date())
    base_xp = min(25, max(2, math.ceil(amount / 100) * 2))
    remaining_cap = max(0, DAILY_HYDRATION_XP_CAP - int(activity["hydration_xp"]))
    xp_awarded = min(base_xp, remaining_cap)
    energy_boost = min(10.0, amount / 125.0)
    happiness_boost = min(6.0, amount / 250.0)
    pet["xp"] = int(pet["xp"]) + xp_awarded
    pet["energy"] = min(100.0, float(pet["energy"]) + energy_boost)
    pet["happiness"] = min(100.0, float(pet["happiness"]) + happiness_boost)
    activity["hydration_ml"] += amount
    activity["hydration_events"] += 1
    activity["xp_earned"] += xp_awarded
    activity["hydration_xp"] += xp_awarded
    events[key] = {
        "amount_ml": amount,
        "xp": xp_awarded,
        "energy_boost": energy_boost,
        "happiness_boost": happiness_boost,
        "awarded_at": current.isoformat(timespec="seconds"),
    }
    while len(events) > MAX_REWARDED_EVENTS:
        del events[next(iter(events))]
    _finish_mutation(pet, current)
    return {
        "awarded": xp_awarded > 0,
        "reason": "awarded" if xp_awarded else "daily_cap",
        "message": (
            f"{pet_name} earned {xp_awarded} XP from your hydration log."
            if xp_awarded
            else f"Today's hydration XP cap is complete; the drink still helped {pet_name}'s mood."
        ),
        "xp_awarded": xp_awarded,
        "event_id": key,
        "snapshot": _decorate_snapshot(pet, current),
    }


def revoke_hydration_xp(
    data: MutableMapping[str, Any],
    amount_ml: int,
    event_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Reverse a previously rewarded hydration event without allowing double revoke."""

    amount = _validate_amount(amount_ml)
    current = _local_now(now)
    pet = _prepare_mutation(data, current)
    events = pet["rewarded_events"]
    key = str(event_id).strip()[:128] if event_id is not None else ""
    if not key:
        matching = [
            (candidate_id, event)
            for candidate_id, event in events.items()
            if int(event.get("amount_ml", 0)) == amount
        ]
        if matching:
            key = max(matching, key=lambda item: str(item[1].get("awarded_at", "")))[0]
    event = events.get(key)
    if not isinstance(event, Mapping):
        return {
            "revoked": False,
            "reason": "event_not_found",
            "message": "No matching pet reward was found to reverse.",
            "xp_revoked": 0,
            "event_id": key or None,
            "snapshot": _decorate_snapshot(pet, current),
        }

    xp_revoked = _safe_int(event.get("xp"), 0, minimum=0, maximum=50)
    pet["xp"] = max(0, int(pet["xp"]) - xp_revoked)
    pet["energy"] = max(0.0, float(pet["energy"]) - float(event.get("energy_boost", 0)))
    pet["happiness"] = max(
        0.0, float(pet["happiness"]) - float(event.get("happiness_boost", 0))
    )
    activity = _roll_daily_activity(pet, current.date())
    try:
        event_day = datetime.fromisoformat(str(event.get("awarded_at"))).date()
    except (TypeError, ValueError):
        event_day = current.date()
    if event_day == current.date():
        activity["hydration_ml"] = max(0, int(activity["hydration_ml"]) - amount)
        activity["hydration_events"] = max(0, int(activity["hydration_events"]) - 1)
        activity["xp_earned"] = max(0, int(activity["xp_earned"]) - xp_revoked)
        activity["hydration_xp"] = max(0, int(activity["hydration_xp"]) - xp_revoked)
    del events[key]
    _finish_mutation(pet, current)
    return {
        "revoked": True,
        "reason": "revoked",
        "message": f"Removed {xp_revoked} XP from the undone hydration log.",
        "xp_revoked": xp_revoked,
        "event_id": key,
        "snapshot": _decorate_snapshot(pet, current),
    }


def care_for_pet(
    data: MutableMapping[str, Any],
    action: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply a bounded care action with both cooldown and daily anti-farming."""

    action_id = str(action or "").strip().casefold().replace("-", "_").replace(" ", "_")
    if action_id not in CARE_ACTIONS:
        raise ValueError(f"Unknown care action: {action!r}.")
    current = _local_now(now)
    pet = _prepare_mutation(data, current)
    pet_name = str(pet.get("name", DEFAULT_PET_NAME))
    care = pet["care"]
    rule = CARE_ACTIONS[action_id]
    day_key = current.date().isoformat()
    counts = care["daily_counts"].setdefault(
        day_key, {candidate: 0 for candidate in CARE_ACTIONS}
    )
    last_raw = care["last_actions"].get(action_id)
    retry_at: datetime | None = None
    if last_raw:
        try:
            retry_at = _local_now(datetime.fromisoformat(str(last_raw))) + timedelta(
                minutes=int(rule["cooldown_minutes"])
            )
        except (TypeError, ValueError):
            retry_at = None
    if retry_at is not None and current < retry_at:
        seconds = max(1, math.ceil((retry_at - current).total_seconds()))
        _finish_mutation(pet, current)
        return {
            "applied": False,
            "reason": "cooldown",
            "message": f"{rule['name']} is ready again in {math.ceil(seconds / 60)} minutes.",
            "xp_awarded": 0,
            "retry_at": retry_at.isoformat(timespec="seconds"),
            "snapshot": _decorate_snapshot(pet, current),
        }
    if int(counts.get(action_id, 0)) >= int(rule["daily_limit"]):
        _finish_mutation(pet, current)
        return {
            "applied": False,
            "reason": "daily_limit",
            "message": f"{pet_name} has had enough {rule['name'].lower()} time for today.",
            "xp_awarded": 0,
            "retry_at": None,
            "snapshot": _decorate_snapshot(pet, current),
        }

    pet["energy"] = max(0.0, min(100.0, float(pet["energy"]) + float(rule["energy"])))
    pet["happiness"] = max(
        0.0, min(100.0, float(pet["happiness"]) + float(rule["happiness"]))
    )
    pet["xp"] = int(pet["xp"]) + int(rule["xp"])
    counts[action_id] = int(counts.get(action_id, 0)) + 1
    care["last_actions"][action_id] = current.isoformat(timespec="seconds")
    activity = _roll_daily_activity(pet, current.date())
    activity["care_actions"] += 1
    activity["xp_earned"] += int(rule["xp"])
    _finish_mutation(pet, current)
    return {
        "applied": True,
        "reason": "applied",
        "message": f"{rule['name']} made {pet_name} feel cared for.",
        "xp_awarded": int(rule["xp"]),
        "retry_at": (
            current + timedelta(minutes=int(rule["cooldown_minutes"]))
        ).isoformat(timespec="seconds"),
        "snapshot": _decorate_snapshot(pet, current),
    }


def rename_pet(data: MutableMapping[str, Any], name: str) -> dict[str, Any]:
    """Rename the pet, rejecting blank, control-heavy, or overlong names."""

    raw_name = " ".join(str(name or "").split())
    if not raw_name or len(raw_name) > 24 or any(not char.isprintable() for char in raw_name):
        raise ValueError("Pet name must contain 1 to 24 printable characters.")
    current = _local_now()
    pet = _prepare_mutation(data, current)
    pet["name"] = raw_name
    profile = data.get("profile")
    if isinstance(profile, MutableMapping):
        profile["mascot_name"] = raw_name
    _finish_mutation(pet, current)
    return _decorate_snapshot(pet, current)


def equip_accessory(
    data: MutableMapping[str, Any], accessory: str
) -> dict[str, Any]:
    """Equip an unlocked accessory, or ``none`` to remove the current one."""

    accessory_id = _accessory_id(accessory)
    if accessory_id not in ACCESSORIES:
        raise ValueError(f"Unknown pet accessory: {accessory!r}.")
    current = _local_now()
    pet = _prepare_mutation(data, current)
    required_level = int(ACCESSORIES[accessory_id]["min_level"])
    if int(pet["level"]) < required_level:
        raise ValueError(
            f"{ACCESSORIES[accessory_id]['name']} unlocks at level {required_level}."
        )
    pet["equipped_accessory"] = accessory_id
    _finish_mutation(pet, current)
    return _decorate_snapshot(pet, current)


def daily_quests(
    data: Mapping[str, Any], now: datetime | None = None
) -> list[dict[str, Any]]:
    """Return today's hydration and companion-care quest progress."""

    if not isinstance(data, Mapping):
        raise TypeError("Water Buddy data must be a mapping.")
    current = _local_now(now)
    day_key = current.date().isoformat()
    records = data.get("daily_records", {})
    record = records.get(day_key, {}) if isinstance(records, Mapping) else {}
    record = record if isinstance(record, Mapping) else {}
    intake = _safe_int(record.get("intake_ml"), 0, minimum=0, maximum=100_000)
    goal = _safe_int(record.get("goal_ml"), 2200, minimum=1, maximum=8000)
    entries = record.get("entries", [])
    log_count = len(entries) if isinstance(entries, list) else int(intake > 0)
    pet = pet_snapshot(data, current)
    activity = pet.get("daily_activity", {})
    care_count = (
        _safe_int(activity.get("care_actions"), 0, minimum=0)
        if isinstance(activity, Mapping) and activity.get("date") == day_key
        else 0
    )
    definitions = (
        ("first_sip", "First ripple", "Log water once today.", "water_drop", log_count, 1, "logs"),
        ("steady_sips", "Steady sips", "Log three separate drinks.", "waves", log_count, 3, "logs"),
        ("daily_goal", "Fill the lagoon", "Reach today's hydration goal.", "flag", intake, goal, "ml"),
        ("buddy_time", "Buddy time", "Care for your Aqualing once.", "favorite", care_count, 1, "actions"),
    )
    quests: list[dict[str, Any]] = []
    for quest_id, title, description, icon, value, target, unit in definitions:
        progress = min(1.0, max(0.0, value / max(1, target)))
        quests.append(
            {
                "id": quest_id,
                "title": title,
                "description": description,
                "icon": icon,
                "current": min(value, target),
                "target": target,
                "unit": unit,
                "progress": progress,
                "complete": value >= target,
            }
        )
    return quests


def daily_quest_summary(
    data: Mapping[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """Return aggregate daily quest completion alongside individual quests."""

    quests = daily_quests(data, now)
    completed = sum(bool(quest["complete"]) for quest in quests)
    return {
        "completed": completed,
        "total": len(quests),
        "progress": completed / max(1, len(quests)),
        "all_complete": completed == len(quests),
        "quests": quests,
    }


__all__ = [
    "ACCESSORIES",
    "CARE_ACTIONS",
    "DEFAULT_PET_NAME",
    "EVOLUTION_STAGES",
    "HOURLY_PET_FACTS",
    "HOURLY_PET_QUOTES",
    "HOURLY_PET_TIPS",
    "LEVEL_XP_THRESHOLDS",
    "MAX_LEVEL",
    "PET_SPECIES",
    "award_hydration_xp",
    "care_for_pet",
    "daily_quest_summary",
    "daily_quests",
    "default_pet_state",
    "equip_accessory",
    "hourly_pet_message",
    "normalize_pet_state",
    "pet_snapshot",
    "rename_pet",
    "revoke_hydration_xp",
]
