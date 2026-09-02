"""Profile, goal, appearance, and local data controls."""

from __future__ import annotations

import json
from datetime import datetime, time

import streamlit as st

from water_buddy.domain import (
    AGE_GOALS,
    DEFAULT_QUICK_LOG_AMOUNTS_ML,
    OCCUPATION_ADJUSTMENTS,
    THEME_OPTIONS,
    calculate_goal,
    default_state,
    normalize_theme,
    set_daily_goal,
    validate_backup_payload,
)
from water_buddy.pet import pet_snapshot, rename_pet
from water_buddy.ui import format_volume, mount_page_ambience, page_intro, render_pet
from water_buddy.units import (
    from_millilitres,
    normalize_units,
    to_millilitres,
    unit_label,
)

mount_page_ambience("profile")

SOUND_VOLUME_OPTIONS = ("Soft", "Balanced", "Vivid")
QUICK_LOG_OPTIONS = (150, 200, 250, 300, 350, 500, 750, 1000)
PENDING_RESTORE_KEY = "pending_water_buddy_restore"


def _parse_time(value: object, fallback: time) -> time:
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except (TypeError, ValueError):
        return fallback


def _adjust_manual_goal(delta: int) -> None:
    units = normalize_units(st.session_state.get("profile_units", "ml"))
    display_value = st.session_state.get("profile_manual_goal_display")
    try:
        current = to_millilitres(display_value, units)
    except ValueError:
        current = int(st.session_state.get("profile_manual_goal", 2200))
    updated = max(500, min(8000, current + delta))
    st.session_state.profile_manual_goal = updated
    st.session_state.profile_manual_goal_display = (
        from_millilitres(updated, units) if units == "oz" else updated
    )
    st.session_state.profile_manual_enabled = True


def _signed_from_millilitres(amount_ml: object, units: object) -> float:
    try:
        amount = float(amount_ml)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    sign = -1.0 if amount < 0 else 1.0
    return sign * from_millilitres(abs(amount), units)


def _signed_to_millilitres(amount: object, units: object) -> int:
    try:
        numeric = float(amount)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Volume adjustment must be numeric.") from error
    sign = -1 if numeric < 0 else 1
    return sign * to_millilitres(abs(numeric), units)


def _format_signed_volume(amount_ml: int, units: object) -> str:
    if amount_ml == 0:
        return format_volume(0, units)
    sign = "+" if amount_ml > 0 else "−"
    return f"{sign}{format_volume(abs(amount_ml), units)}"


def _persist_experience_preference(
    preference_key: str,
    widget_key: str,
    allowed_values: tuple[str, ...] | None = None,
) -> None:
    """Persist one experience control before Streamlit's normal rerun."""

    value = st.session_state.get(widget_key)
    if allowed_values is not None:
        value = value if value in allowed_values else allowed_values[0]
    elif preference_key in {"background_motion", "sound_enabled"}:
        value = bool(value)

    data = st.session_state["data"]
    preferences = data.setdefault("preferences", {})
    if not isinstance(preferences, dict):
        preferences = {}
        data["preferences"] = preferences
    if preference_key == "units":
        previous_units = normalize_units(preferences.get("units", "ml"))
        next_units = normalize_units(value)
        if previous_units != next_units:
            custom_display = st.session_state.get("profile_custom_adjustment_display")
            if custom_display is not None:
                custom_ml = _signed_to_millilitres(custom_display, previous_units)
                st.session_state.profile_custom_adjustment = custom_ml
                st.session_state.profile_custom_adjustment_display = (
                    _signed_from_millilitres(custom_ml, next_units)
                    if next_units == "oz"
                    else custom_ml
                )
            manual_display = st.session_state.get("profile_manual_goal_display")
            if manual_display is not None:
                manual_ml = to_millilitres(manual_display, previous_units)
                manual_ml = max(500, min(8000, manual_ml))
                st.session_state.profile_manual_goal = manual_ml
                st.session_state.profile_manual_goal_display = (
                    from_millilitres(manual_ml, next_units)
                    if next_units == "oz"
                    else manual_ml
                )
        value = next_units
    preferences[preference_key] = value
    st.session_state["store"].save(data)
    labels = {
        "theme": "App theme updated.",
        "background_motion": "Motion preference updated.",
        "units": "Volume display updated.",
        "sound_enabled": "Interface sound preference updated.",
        "interface_sound_volume": "Click volume updated.",
    }
    st.session_state.flash_message = labels.get(
        preference_key,
        "Experience preference updated.",
    )


def _clear_profile_widget_state() -> None:
    for key in list(st.session_state):
        if key.startswith("profile_"):
            del st.session_state[key]


def _quick_log_defaults(raw: object) -> list[int]:
    """Return four safe, distinct values accepted by the preset control."""

    if isinstance(raw, (list, tuple)):
        selected: list[int] = []
        for value in raw:
            if isinstance(value, bool):
                continue
            try:
                amount = int(value)
            except (TypeError, ValueError, OverflowError):
                continue
            if 1 <= amount <= 5000 and amount not in selected:
                selected.append(amount)
        if len(selected) == 4:
            return selected
    return list(DEFAULT_QUICK_LOG_AMOUNTS_ML)


@st.dialog("Reset Water Buddy?", icon=":material/delete_forever:")
def _confirm_full_reset() -> None:
    st.error(
        "This permanently clears your profile, pet, hydration logs, streak, and badges on this device.",
        icon=":material/warning:",
    )
    st.caption("Export a backup first if you might want this history later.")
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel", key="cancel_full_reset"):
            st.rerun()
        if st.button(
            "Delete local data",
            type="primary",
            icon=":material/delete_forever:",
            key="confirm_full_reset",
        ):
            fresh = default_state()
            st.session_state.store.save(fresh)
            st.session_state.data.clear()
            st.session_state.data.update(fresh)
            _clear_profile_widget_state()
            st.session_state.flash_message = (
                "Water Buddy has been reset to a fresh profile."
            )
            st.rerun()


@st.dialog("Restore this backup?", icon=":material/settings_backup_restore:")
def _confirm_restore() -> None:
    """Preview a validated backup before replacing the mounted profile."""

    candidate = st.session_state.get(PENDING_RESTORE_KEY)
    if not isinstance(candidate, dict):
        st.info("Choose and validate a Water Buddy backup first.")
        return

    candidate_profile = candidate.get("profile", {})
    candidate_preferences = candidate.get("preferences", {})
    records = candidate.get("daily_records", {})
    record_values = records.values() if isinstance(records, dict) else ()
    total_ml = sum(
        max(0, int(record.get("intake_ml", 0)))
        for record in record_values
        if isinstance(record, dict)
    )
    display_units = (
        candidate_preferences.get("units", "ml")
        if isinstance(candidate_preferences, dict)
        else "ml"
    )
    candidate_name = (
        str(candidate_profile.get("name", "Hydration hero"))
        if isinstance(candidate_profile, dict)
        else "Hydration hero"
    )

    st.warning(
        "Restoring replaces this account’s current profile, settings, pet, and "
        "hydration history. Export the current profile first if you may need it.",
        icon=":material/warning:",
    )
    with st.container(horizontal=True):
        st.metric("Profile", candidate_name, border=True)
        st.metric("History days", len(records) if isinstance(records, dict) else 0, border=True)
        st.metric("Journey volume", format_volume(total_ml, display_units), border=True)

    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Cancel restore", key="cancel_restore_backup"):
            st.session_state.pop(PENDING_RESTORE_KEY, None)
            st.rerun()
        if st.button(
            "Restore backup",
            type="primary",
            icon=":material/settings_backup_restore:",
            key="confirm_restore_backup",
        ):
            data = st.session_state.data
            st.session_state.store.save(candidate)
            data.clear()
            data.update(candidate)
            st.session_state.pop(PENDING_RESTORE_KEY, None)
            _clear_profile_widget_state()
            st.session_state.flash_message = "Backup restored successfully."
            st.rerun()


data = st.session_state.data
profile = data.setdefault("profile", {})
preferences = data.setdefault("preferences", {})
pet = pet_snapshot(data)

current_auto_goal = calculate_goal(
    profile.get("age_group", next(iter(AGE_GOALS))),
    profile.get("occupation", "Office Worker"),
    int(profile.get("custom_adjustment_ml", 0) or 0),
)
initial_units = normalize_units(preferences.get("units", "ml"))
initial_custom_adjustment = int(profile.get("custom_adjustment_ml", 0) or 0)
initial_manual_goal = int(profile.get("manual_goal_ml") or current_auto_goal)

defaults = {
    "profile_name": profile.get("name", "Hydration hero"),
    "profile_mascot_name": pet.get("name", "Ripple"),
    "profile_age_group": profile.get("age_group", next(iter(AGE_GOALS))),
    "profile_occupation": profile.get("occupation", "Office Worker"),
    "profile_custom_adjustment": initial_custom_adjustment,
    "profile_custom_adjustment_display": (
        _signed_from_millilitres(initial_custom_adjustment, initial_units)
        if initial_units == "oz"
        else initial_custom_adjustment
    ),
    "profile_manual_enabled": profile.get("manual_goal_ml") is not None,
    "profile_manual_goal": initial_manual_goal,
    "profile_manual_goal_display": (
        from_millilitres(initial_manual_goal, initial_units)
        if initial_units == "oz"
        else initial_manual_goal
    ),
    "profile_wake_time": _parse_time(profile.get("wake_time"), time(7, 0)),
    "profile_sleep_time": _parse_time(profile.get("sleep_time"), time(22, 0)),
    "profile_theme": normalize_theme(preferences.get("theme", "Dark")),
    "profile_background_motion": bool(preferences.get("background_motion", True)),
    "profile_units": initial_units,
    "profile_sound_enabled": bool(preferences.get("sound_enabled", True)),
    "profile_interface_sound_volume": (
        str(preferences.get("interface_sound_volume", "Balanced")).title()
        if str(preferences.get("interface_sound_volume", "Balanced")).title()
        in SOUND_VOLUME_OPTIONS
        else "Balanced"
    ),
    "profile_quick_log_amounts": _quick_log_defaults(
        preferences.get("quick_log_amounts_ml", DEFAULT_QUICK_LOG_AMOUNTS_ML)
    ),
}
for state_key, default_value in defaults.items():
    st.session_state.setdefault(state_key, default_value)

page_intro(
    "Make it yours",
    "Profile & plan",
    "Tune your goal to your life, personalize your pet, and keep control of your local data.",
    "Local profile",
)

identity, preview = st.columns([1.25, 0.75], gap="large", vertical_alignment="center")
with identity:
    with st.container(border=True):
        st.subheader("Your Water Buddy")
        st.text_input(
            "Your name",
            key="profile_name",
            max_chars=48,
            placeholder="How should your buddy greet you?",
        )
        st.text_input(
            "Pet name",
            key="profile_mascot_name",
            max_chars=24,
            help="This name follows your companion across every page.",
        )
with preview:
    preview_pet = dict(pet)
    preview_pet["name"] = st.session_state.profile_mascot_name or "Ripple"
    preview_pet["speech"] = "Looking good! I’ll use this name everywhere."
    render_pet(preview_pet, 0.72, compact=True)

with st.container(border=True):
    st.subheader("Personalized daily goal")
    st.caption("Your recommendation combines an age baseline with your daily occupation.")
    goal_units = normalize_units(st.session_state.profile_units)
    imperial_goal_display = goal_units == "oz"

    age_col, occupation_col = st.columns(2)
    age_col.selectbox(
        "Age group",
        list(AGE_GOALS),
        key="profile_age_group",
        format_func=lambda option: (
            f"{option} · {format_volume(AGE_GOALS[option], goal_units)}"
        ),
    )
    occupation_col.selectbox(
        "Occupation",
        list(OCCUPATION_ADJUSTMENTS),
        key="profile_occupation",
        format_func=lambda option: (
            f"{option} · {_format_signed_volume(OCCUPATION_ADJUSTMENTS[option], goal_units)}"
            if OCCUPATION_ADJUSTMENTS[option] > 0
            else option
        ),
    )

    custom_adjustment_display = st.number_input(
        f"Custom occupation adjustment ({unit_label(goal_units)})",
        min_value=(
            -from_millilitres(500, "oz") if imperial_goal_display else -500
        ),
        max_value=(
            from_millilitres(3000, "oz") if imperial_goal_display else 3000
        ),
        step=1.0 if imperial_goal_display else 50,
        format="%.1f" if imperial_goal_display else "%d",
        key="profile_custom_adjustment_display",
        disabled=st.session_state.profile_occupation != "Custom",
        help="Used only when occupation is set to Custom.",
    )
    custom_adjustment_ml = _signed_to_millilitres(
        custom_adjustment_display,
        goal_units,
    )
    st.session_state.profile_custom_adjustment = custom_adjustment_ml

    automatic_goal = calculate_goal(
        st.session_state.profile_age_group,
        st.session_state.profile_occupation,
        custom_adjustment_ml,
    )
    st.toggle(
        "Set my own daily goal",
        key="profile_manual_enabled",
        help="Turn this off anytime to return to the automatic recommendation.",
    )

    goal_minus, goal_input, goal_plus = st.columns([0.25, 1, 0.25], vertical_alignment="bottom")
    goal_minus.button(
        f"−{format_volume(250, goal_units)}",
        key="goal_minus_250",
        on_click=_adjust_manual_goal,
        args=(-250,),
        width="stretch",
    )
    manual_goal_display = goal_input.number_input(
        f"Daily goal ({unit_label(goal_units)})",
        min_value=(
            from_millilitres(500, "oz") if imperial_goal_display else 500
        ),
        max_value=(
            from_millilitres(8000, "oz") if imperial_goal_display else 8000
        ),
        step=1.0 if imperial_goal_display else 50,
        format="%.1f" if imperial_goal_display else "%d",
        key="profile_manual_goal_display",
        disabled=not st.session_state.profile_manual_enabled,
    )
    manual_goal_ml = max(
        500,
        min(8000, to_millilitres(manual_goal_display, goal_units)),
    )
    st.session_state.profile_manual_goal = manual_goal_ml
    goal_plus.button(
        f"+{format_volume(250, goal_units)}",
        key="goal_plus_250",
        on_click=_adjust_manual_goal,
        args=(250,),
        width="stretch",
    )

    final_goal = (
        manual_goal_ml
        if st.session_state.profile_manual_enabled
        else automatic_goal
    )
    with st.container(horizontal=True):
        st.metric(
            "Age baseline",
            format_volume(
                AGE_GOALS[st.session_state.profile_age_group],
                goal_units,
            ),
            border=True,
        )
        adjustment = final_goal - AGE_GOALS[st.session_state.profile_age_group]
        st.metric(
            "Plan adjustment",
            _format_signed_volume(adjustment, goal_units),
            border=True,
        )
        st.metric(
            "Your daily goal",
            format_volume(final_goal, goal_units),
            border=True,
        )

    quick_log_display_units = st.session_state.profile_units
    quick_log_options = tuple(
        sorted(
            set(QUICK_LOG_OPTIONS).union(
                st.session_state.profile_quick_log_amounts
            )
        )
    )
    quick_log_amounts = st.multiselect(
        "Quick-log presets",
        options=quick_log_options,
        key="profile_quick_log_amounts",
        max_selections=4,
        format_func=lambda amount: format_volume(amount, quick_log_display_units),
        help="Choose exactly four amounts for the one-tap buttons on Home and Log water.",
    )
    quick_log_amounts_valid = len(quick_log_amounts) == 4
    if not quick_log_amounts_valid:
        st.warning(
            "Choose exactly four quick-log amounts before saving your plan.",
            icon=":material/info:",
        )

schedule, experience = st.columns(2, gap="large")
with schedule:
    with st.container(border=True, height="stretch"):
        st.subheader("Daily rhythm")
        st.caption("Used for pace calculations and quiet reminder hours.")
        st.time_input("Wake-up time", key="profile_wake_time")
        st.time_input("Sleep time", key="profile_sleep_time")

with experience:
    with st.container(border=True, height="stretch"):
        st.subheader("Experience")
        st.caption("These controls save instantly and apply across Water Buddy.")
        st.segmented_control(
            "App theme",
            THEME_OPTIONS,
            key="profile_theme",
            required=True,
            on_change=_persist_experience_preference,
            args=("theme", "profile_theme", THEME_OPTIONS),
            width="stretch",
        )
        st.toggle(
            "Motion effects",
            key="profile_background_motion",
            help="Turn off ambient bubbles, pet motion, and decorative transitions for a calmer experience.",
            on_change=_persist_experience_preference,
            args=("background_motion", "profile_background_motion"),
        )
        st.segmented_control(
            "Volume display",
            ["ml", "oz"],
            key="profile_units",
            required=True,
            on_change=_persist_experience_preference,
            args=("units", "profile_units", ("ml", "oz")),
        )
        st.toggle(
            "Interface sounds",
            key="profile_sound_enabled",
            help="Master switch for button, water-log, reset, and celebration sounds.",
            on_change=_persist_experience_preference,
            args=("sound_enabled", "profile_sound_enabled"),
        )
        st.segmented_control(
            "Click volume",
            SOUND_VOLUME_OPTIONS,
            key="profile_interface_sound_volume",
            required=True,
            disabled=not bool(st.session_state.profile_sound_enabled),
            on_change=_persist_experience_preference,
            args=(
                "interface_sound_volume",
                "profile_interface_sound_volume",
                SOUND_VOLUME_OPTIONS,
            ),
            width="stretch",
        )

if st.button(
    "Save profile & plan",
    type="primary",
    icon=":material/save:",
    key="save_profile_plan",
    width="stretch",
    disabled=not quick_log_amounts_valid,
):
    clean_name = str(st.session_state.profile_name).strip() or "Hydration hero"
    clean_mascot_name = str(st.session_state.profile_mascot_name).strip() or "Ripple"
    rename_pet(data, clean_mascot_name)
    profile.update(
        {
            "name": clean_name,
            "mascot_name": clean_mascot_name,
            "age_group": st.session_state.profile_age_group,
            "occupation": st.session_state.profile_occupation,
            "custom_adjustment_ml": custom_adjustment_ml,
            "manual_goal_ml": (
                manual_goal_ml
                if st.session_state.profile_manual_enabled
                else None
            ),
            "wake_time": st.session_state.profile_wake_time.strftime("%H:%M"),
            "sleep_time": st.session_state.profile_sleep_time.strftime("%H:%M"),
        }
    )
    preferences.update(
        {
            "theme": st.session_state.profile_theme,
            "background_motion": bool(st.session_state.profile_background_motion),
            "units": st.session_state.profile_units,
            "sound_enabled": bool(st.session_state.profile_sound_enabled),
            "interface_sound_volume": st.session_state.profile_interface_sound_volume,
            "quick_log_amounts_ml": list(st.session_state.profile_quick_log_amounts),
        }
    )
    set_daily_goal(data, final_goal)
    st.session_state.store.save(data)
    st.session_state.flash_message = "Your profile and hydration plan are updated."
    st.rerun()

st.subheader("Your data")
backup, restore = st.columns(2, gap="large")
with backup:
    with st.container(border=True, height="stretch"):
        st.markdown("**Export a backup**")
        st.caption("Download your complete profile, settings, and history as readable JSON.")
        st.download_button(
            "Download Water Buddy data",
            data=json.dumps(data, indent=2, ensure_ascii=False),
            file_name=f"water-buddy-backup-{datetime.now():%Y-%m-%d}.json",
            mime="application/json",
            icon=":material/download:",
            width="stretch",
        )

with restore:
    with st.container(border=True, height="stretch"):
        st.markdown("**Restore a backup**")
        uploaded_backup = st.file_uploader(
            "Choose a Water Buddy JSON backup",
            type=["json"],
            key="restore_backup_file",
        )
        if uploaded_backup is not None and st.button(
            "Validate backup",
            icon=":material/upload:",
            key="restore_backup_button",
            width="stretch",
        ):
            raw = uploaded_backup.getvalue()
            if len(raw) > 1_000_000:
                st.error("That backup is larger than 1 MB and cannot be restored safely.")
            else:
                try:
                    restored = json.loads(raw.decode("utf-8"))
                    if not isinstance(restored, dict):
                        raise ValueError("Backup root must be a JSON object.")
                    normalized = validate_backup_payload(restored)
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as error:
                    st.error(f"This file is not a valid Water Buddy backup: {error}")
                else:
                    st.session_state[PENDING_RESTORE_KEY] = normalized
                    _confirm_restore()

with st.expander("Danger zone", icon=":material/warning:"):
    st.caption("This action cannot be undone unless you export a backup first.")
    if st.button(
        "Reset all local data",
        icon=":material/delete_forever:",
        key="open_full_reset",
    ):
        _confirm_full_reset()

st.caption(
    f"Current goal preview: {format_volume(final_goal, st.session_state.profile_units)}. "
    "Water Buddy stores all calculations internally in millilitres for accuracy."
)
