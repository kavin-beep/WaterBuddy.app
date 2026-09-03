"""Local hydration reminder controls and in-app reminder actions."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any

import streamlit as st

from water_buddy.clock import local_now
from water_buddy.domain import (
    dismiss_reminder,
    progress_summary,
    reminder_is_due,
    snooze_reminder,
)
from water_buddy.pet import pet_snapshot
from water_buddy.ui import mount_page_ambience, page_intro, render_pet

mount_page_ambience("reminders")


def _clock(value: Any, fallback: time) -> time:
    if isinstance(value, datetime):
        return value.time().replace(second=0, microsecond=0)
    if isinstance(value, time):
        return value.replace(second=0, microsecond=0)
    try:
        return time.fromisoformat(str(value)).replace(second=0, microsecond=0)
    except (TypeError, ValueError):
        return fallback


def _moment(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        return local_now(parsed)
    return parsed


def _whole_number(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _next_reminder_label(value: Any) -> tuple[str, str]:
    scheduled = _moment(value)
    if scheduled is None:
        return "Not scheduled", "Save reminder settings to create the next alert."
    now = local_now()
    seconds = (scheduled - now).total_seconds()
    if seconds <= 0:
        relative = "Due now"
    elif seconds < 3600:
        minutes = max(1, round(seconds / 60))
        relative = f"In {minutes} minute{'s' if minutes != 1 else ''}"
    elif scheduled.date() == now.date():
        relative = f"Today at {scheduled.strftime('%H:%M')}"
    else:
        relative = scheduled.strftime("%a, %d %b at %H:%M")
    return scheduled.strftime("%H:%M"), relative


data = st.session_state["data"]
store = st.session_state["store"]
profile = data.setdefault("profile", {})
preferences = data.setdefault("preferences", {})

page_intro(
    "Reminders",
    "Gentle nudges, on your schedule",
    "Choose when Water Buddy should check in, protect quiet hours, and keep each reminder easy to act on.",
    "In-app reminders",
)

is_enabled = bool(preferences.get("reminders_enabled", True))
goal_complete = bool(progress_summary(data).get("goal_met"))
next_time, next_relative = _next_reminder_label(preferences.get("next_reminder_at"))

with st.container(horizontal=True):
    st.metric(
        "Reminder status",
        "Resting" if is_enabled and goal_complete else "Active" if is_enabled else "Paused",
        border=True,
    )
    st.metric(
        "Next reminder",
        "Tomorrow" if is_enabled and goal_complete else next_time if is_enabled else "Paused",
        (
            "Today’s goal is complete"
            if is_enabled and goal_complete
            else next_relative
            if is_enabled
            else "Enable reminders to resume"
        ),
        border=True,
    )
    st.metric(
        "Interval",
        f"{_whole_number(preferences.get('reminder_interval_minutes'), 45)} min",
        border=True,
    )

if is_enabled and goal_complete:
    st.success(
        "Today’s goal is complete, so scheduled hydration nudges are resting until tomorrow.",
        icon=":material/check_circle:",
    )

due_now = bool(is_enabled and reminder_is_due(data))
test_active = bool(st.session_state.get("reminders_test_active", False))
if due_now or test_active:
    with st.container(border=True):
        alert_title = "This is a test reminder" if test_active and not due_now else "Time to drink water"
        st.warning(
            f"{alert_title}. Take a comfortable sip, then choose what Water Buddy should do next.",
            icon=":material/notifications_active:",
        )
        with st.container(horizontal=True):
            if st.button(
                "Snooze 10 minutes",
                icon=":material/snooze:",
                key="reminders_due_snooze",
                disabled=not is_enabled,
            ):
                snooze_reminder(data, 10)
                st.session_state["reminders_test_active"] = False
                store.save(data)
                st.toast("Reminder snoozed for 10 minutes.", icon=":material/snooze:")
                st.rerun()
            if st.button(
                "Dismiss",
                icon=":material/check:",
                key="reminders_due_dismiss",
                type="primary",
            ):
                if is_enabled:
                    dismiss_reminder(data)
                st.session_state["reminders_test_active"] = False
                preferences["last_reminder_dismissed_at"] = local_now().isoformat(
                    timespec="seconds"
                )
                store.save(data)
                st.toast("Reminder dismissed.", icon=":material/check_circle:")
                st.rerun()

settings_column, preview_column = st.columns([1.45, 1], vertical_alignment="top")
with settings_column:
    with st.form("reminder_settings"):
        st.subheader("Reminder schedule")
        enabled = st.toggle(
            "Enable hydration reminders",
            value=is_enabled,
            help="Water Buddy checks this schedule while the app is open in your browser.",
        )
        interval = st.selectbox(
            "Reminder interval",
            options=[15, 30, 45, 60, 90, 120],
            index=[15, 30, 45, 60, 90, 120].index(
                _whole_number(preferences.get("reminder_interval_minutes"), 45)
                if _whole_number(preferences.get("reminder_interval_minutes"), 45) in [15, 30, 45, 60, 90, 120]
                else 45
            ),
            format_func=lambda minutes: f"Every {minutes} minutes",
        )
        st.caption("Active window")
        wake_column, sleep_column = st.columns(2)
        wake_time = wake_column.time_input(
            "Wake time",
            value=_clock(profile.get("wake_time"), time(7, 0)),
            step=900,
        )
        sleep_time = sleep_column.time_input(
            "Sleep time",
            value=_clock(profile.get("sleep_time"), time(22, 30)),
            step=900,
        )
        st.caption("Quiet hours")
        quiet_start_column, quiet_end_column = st.columns(2)
        quiet_start = quiet_start_column.time_input(
            "Quiet from",
            value=_clock(preferences.get("quiet_start"), time(22, 0)),
            step=900,
        )
        quiet_end = quiet_end_column.time_input(
            "Quiet until",
            value=_clock(preferences.get("quiet_end"), time(7, 0)),
            step=900,
        )
        saved = st.form_submit_button(
            "Save reminder settings",
            icon=":material/save:",
            type="primary",
        )

    if saved:
        previous_interval = _whole_number(
            preferences.get("reminder_interval_minutes"), 45
        )
        preferences["reminders_enabled"] = bool(enabled)
        preferences["reminder_interval_minutes"] = int(interval)
        preferences["quiet_start"] = quiet_start.strftime("%H:%M")
        preferences["quiet_end"] = quiet_end.strftime("%H:%M")
        profile["wake_time"] = wake_time.strftime("%H:%M")
        profile["sleep_time"] = sleep_time.strftime("%H:%M")
        if enabled:
            if not preferences.get("next_reminder_at") or previous_interval != int(interval) or not is_enabled:
                preferences["next_reminder_at"] = (
                    local_now() + timedelta(minutes=int(interval))
                ).isoformat(timespec="seconds")
        else:
            preferences["next_reminder_at"] = None
            st.session_state["reminders_test_active"] = False
        store.save(data)
        st.toast("Reminder settings saved.", icon=":material/check_circle:")
        st.rerun()

with preview_column:
    reminder_pet = pet_snapshot(data)
    reminder_pet["speech"] = (
        "I’ll nudge you gently when it is time for another sip."
        if is_enabled
        else "I’ll stay quiet until you turn reminders back on."
    )
    render_pet(reminder_pet, 0.55 if is_enabled else 0.15, compact=True)
    with st.container(border=True):
        st.markdown(":material/info: **How reminders work**")
        st.write(
            "Reminders are checked while this app tab is open and active. Water Buddy does not run a background service when the tab or app is closed."
        )
        st.caption(
            "Quiet hours and your wake/sleep window prevent nudges at inconvenient times."
        )

st.subheader("Try the reminder flow")
st.write("Testing shows the same in-app prompt without changing your next scheduled reminder.")
with st.container(horizontal=True):
    if st.button(
        "Test reminder",
        icon=":material/notifications:",
        key="reminders_test",
    ):
        st.session_state["reminders_test_active"] = True
        preferences["last_test_reminder_at"] = local_now().isoformat(
            timespec="seconds"
        )
        store.save(data)
        st.toast("Test reminder triggered.", icon=":material/notifications_active:")
        st.rerun()
    if st.button(
        "Snooze next reminder",
        icon=":material/snooze:",
        key="reminders_snooze_next",
        disabled=not is_enabled,
    ):
        snooze_reminder(data, 10)
        store.save(data)
        st.toast("Next reminder moved back 10 minutes.", icon=":material/schedule:")
        st.rerun()
    if st.button(
        "Dismiss and reschedule",
        icon=":material/done_all:",
        key="reminders_dismiss_next",
        disabled=not is_enabled,
    ):
        dismiss_reminder(data)
        preferences["last_reminder_dismissed_at"] = local_now().isoformat(
            timespec="seconds"
        )
        store.save(data)
        st.toast("Next reminder scheduled from now.", icon=":material/check_circle:")
        st.rerun()
