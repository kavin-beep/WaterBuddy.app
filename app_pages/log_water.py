"""Focused water logging and today's entry management."""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd
import streamlit as st

from water_buddy.clock import APP_TIMEZONE
from water_buddy.domain import (
    WATER_LOG_COOLDOWN_SECONDS,
    WaterLogCooldownError,
    add_water,
    progress_summary,
    reset_day,
    undo_last_water,
    water_log_cooldown_remaining,
)
from water_buddy.pet import pet_snapshot
from water_buddy.ui import (
    format_volume,
    mount_page_ambience,
    page_intro,
    render_bottle,
    render_empty_state,
    render_pet,
)
from water_buddy.units import to_millilitres, unit_label

mount_page_ambience("log")

SOURCES = ("Glass", "Bottle", "Meal", "Workout", "Reminder", "Other")
SIP_GUARD_NOTICE_KEY = "log_water_sip_guard_notice"


def _cooldown_seconds(error: WaterLogCooldownError | None = None) -> int:
    """Return a display-safe, upward-rounded Sip Guard countdown."""

    if error is not None:
        try:
            return max(0, math.ceil(float(error.retry_after_seconds)))
        except (TypeError, ValueError, OverflowError):
            pass
    try:
        remaining = water_log_cooldown_remaining(st.session_state.data)
        return max(0, math.ceil(float(remaining)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _sip_guard_message(remaining_seconds: int) -> str:
    wait_text = (
        f" Try again in about {remaining_seconds} second"
        f"{'s' if remaining_seconds != 1 else ''}."
        if remaining_seconds > 0
        else " You can log again now."
    )
    return (
        "Sip Guard prevented a likely accidental double-count."
        f"{wait_text} The {WATER_LOG_COOLDOWN_SECONDS}-second guard protects the log "
        "only—it is not a "
        "recommendation about how often to drink water."
    )


def _remember_guard_block(error: WaterLogCooldownError) -> int:
    remaining = _cooldown_seconds(error)
    st.session_state[SIP_GUARD_NOTICE_KEY] = {
        "remaining_seconds": remaining,
        "user_message": error.user_message,
    }
    # A blocked add must never inherit or trigger success audio.
    st.session_state.sound_event = None
    st.session_state.flash_message = None
    return remaining


def _clear_guard_notice() -> None:
    st.session_state.pop(SIP_GUARD_NOTICE_KEY, None)


@st.fragment(run_every="1s")
def _render_sip_guard_status() -> None:
    """Refresh only the small guard status while its countdown is active."""

    remaining = _cooldown_seconds()
    notice = st.session_state.get(SIP_GUARD_NOTICE_KEY)
    if notice and remaining > 0:
        st.warning(
            _sip_guard_message(remaining),
            icon=":material/shield:",
        )
    elif notice:
        _clear_guard_notice()
        st.rerun()
    elif remaining > 0:
        st.caption(
            f":material/timer: Sip Guard · another entry is available in {remaining} second"
            f"{'s' if remaining != 1 else ''}."
        )
    else:
        st.rerun()


def _persist(message: str) -> None:
    st.session_state.store.save(st.session_state.data)
    st.session_state.flash_message = message


def _quick_add(amount_ml: int) -> None:
    data = st.session_state.data
    before = progress_summary(data)["progress"]
    try:
        after = add_water(data, amount_ml, source="Quick log")
    except WaterLogCooldownError as error:
        _remember_guard_block(error)
        return
    _clear_guard_notice()
    if before < 1 <= after["progress"]:
        st.session_state.celebrate_once = True
        st.session_state.sound_event = "goal"
    else:
        st.session_state.sound_event = "water"
    units = data.get("preferences", {}).get("units", "ml")
    _persist(f"{format_volume(amount_ml, units)} added.")


def _undo_last() -> None:
    if undo_last_water(st.session_state.data):
        _clear_guard_notice()
        st.session_state.sound_event = "reset"
        _persist("Last water entry removed.")
    else:
        st.session_state.flash_message = "There is no entry to undo."


@st.dialog("Reset today?", icon=":material/restart_alt:")
def _confirm_reset() -> None:
    summary = progress_summary(st.session_state.data)
    units = st.session_state.data.get("preferences", {}).get("units", "ml")
    st.warning(
        f"This clears today’s {format_volume(summary['intake_ml'], units)} and all "
        "of today’s entries. "
        "Your profile and earlier history stay safe.",
        icon=":material/warning:",
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Keep my entries", key="cancel_reset_today"):
            st.rerun()
        if st.button(
            "Reset today",
            type="primary",
            icon=":material/delete_sweep:",
            key="confirm_reset_today",
        ):
            reset_day(st.session_state.data)
            _clear_guard_notice()
            st.session_state.sound_event = "reset"
            _persist("Today has been reset. Fresh start, no judgment.")
            st.session_state.celebrate_once = False
            st.rerun()


data = st.session_state.data
preferences = data.get("preferences", {})
summary = progress_summary(data)
units = preferences.get("units", "ml")
quick_amounts = preferences.get("quick_log_amounts_ml", (250, 500, 750, 1000))
if not isinstance(quick_amounts, (list, tuple)) or len(quick_amounts) != 4:
    quick_amounts = (250, 500, 750, 1000)

page_intro(
    "Add a sip",
    "Log water",
    "Fast enough for a single tap, detailed enough to keep your daily history useful.",
    "Auto-saved",
)

with st.container(border=True, key="log-quick-card"):
    st.subheader("Quick amounts")
    st.caption("Choose the closest amount — consistency matters more than perfect measuring.")
    if st.session_state.get(SIP_GUARD_NOTICE_KEY) or water_log_cooldown_remaining(data) > 0:
        _render_sip_guard_status()
    else:
        st.caption(
            ":material/shield: Sip Guard ready · protects against accidental double-counts."
        )
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        for amount in quick_amounts:
            amount = int(amount)
            st.button(
                f"+{format_volume(amount, units)}",
                key=f"log_quick_{amount}",
                icon=":material/add:",
                on_click=_quick_add,
                args=(amount,),
                type="primary" if amount == quick_amounts[0] else "secondary",
                width="stretch",
            )

status, visual = st.columns([1.35, 0.85], gap="large", vertical_alignment="center")
with status:
    with st.container(border=True):
        st.subheader("Today at a glance")
        with st.container(horizontal=True):
            st.metric(
                "Consumed",
                format_volume(summary["intake_ml"], units),
                border=True,
            )
            st.metric(
                "Remaining",
                format_volume(summary["remaining_ml"], units),
                border=True,
            )
            st.metric(
                "Progress",
                f"{summary['percentage']:.0f}%",
                border=True,
            )
        st.progress(
            min(summary["progress"], 1.0),
            text=f"{format_volume(summary['intake_ml'], units)} of {format_volume(summary['goal_ml'], units)}",
        )
with visual:
    logging_pet = pet_snapshot(data)
    logging_pet["speech"] = "I react to every milestone you reach."
    render_pet(logging_pet, summary["progress"], compact=True)

custom, bottle = st.columns([1.25, 0.75], gap="large", vertical_alignment="center")
with custom:
    with st.container(border=True):
        st.subheader("Custom entry")
        with st.form("custom_water_entry", border=False):
            imperial = str(units).casefold() == "oz"
            amount_display = st.number_input(
                f"Amount ({unit_label(units)})",
                min_value=2.0 if imperial else 50,
                max_value=101.0 if imperial else 3000,
                value=10.0 if imperial else 300,
                step=1.0 if imperial else 50,
                key="custom_log_amount",
            )
            source = st.selectbox("Where did you drink it?", SOURCES, key="custom_log_source")
            submitted = st.form_submit_button(
                "Add to today",
                type="primary",
                icon=":material/add_circle:",
                width="stretch",
            )
        if submitted:
            amount_ml = to_millilitres(amount_display, units)
            before = progress_summary(data)["progress"]
            try:
                after = add_water(data, int(amount_ml), source=source)
            except WaterLogCooldownError as error:
                remaining = _remember_guard_block(error)
                st.warning(
                    _sip_guard_message(remaining),
                    icon=":material/shield:",
                )
            else:
                _clear_guard_notice()
                if before < 1 <= after["progress"]:
                    st.session_state.celebrate_once = True
                    st.session_state.sound_event = "goal"
                else:
                    st.session_state.sound_event = "water"
                _persist(f"{format_volume(amount_ml, units)} added from {source.lower()}.")
                st.rerun()

        with st.container(horizontal=True, horizontal_alignment="right"):
            st.button(
                "Undo last",
                icon=":material/undo:",
                key="undo_last_water",
                on_click=_undo_last,
                disabled=not bool(summary.get("entries")),
            )
            if st.button(
                "Reset day",
                icon=":material/restart_alt:",
                key="open_reset_today",
            ):
                _confirm_reset()

with bottle:
    render_bottle(
        summary["progress"],
        summary["intake_ml"],
        summary["goal_ml"],
        units,
    )

st.subheader("Today’s entries")
entries = list(reversed(summary.get("entries", [])))
if entries:
    rows: list[dict[str, object]] = []
    for entry in entries:
        raw_time = str(entry.get("logged_at", ""))
        try:
            logged_moment = datetime.fromisoformat(raw_time)
            if logged_moment.tzinfo is not None:
                logged_moment = logged_moment.astimezone(APP_TIMEZONE)
            logged_at = logged_moment.strftime("%I:%M %p")
        except ValueError:
            logged_at = "Unknown"
        rows.append(
            {
                "time": logged_at,
                "amount": format_volume(int(entry.get("amount_ml", 0)), units),
                "source": str(entry.get("source", "Water")),
            }
        )

    entries_frame = pd.DataFrame(rows)
    st.dataframe(
        entries_frame,
        hide_index=True,
        column_config={
            "time": st.column_config.TextColumn("Time", pinned=True),
            "amount": st.column_config.TextColumn("Amount"),
            "source": st.column_config.TextColumn("Source"),
        },
        key="today_entries_table",
    )

else:
    render_empty_state(
        "Your timeline is ready",
        "Log your first glass and it will appear here with its time and source.",
    )
