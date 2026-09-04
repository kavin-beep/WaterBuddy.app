"""The Water Buddy daily home dashboard."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from water_buddy.clock import current_timezone, local_now
from water_buddy.domain import (
    WATER_LOG_COOLDOWN_SECONDS,
    WaterLogCooldownError,
    add_water,
    calculate_streak,
    history_rows,
    progress_summary,
    water_log_cooldown_remaining,
)
from water_buddy.pet import pet_snapshot
from water_buddy.ui import (
    celebration_confetti,
    format_volume,
    mount_page_ambience,
    page_intro,
    render_bottle,
    render_hourly_pet,
)

mount_page_ambience("home")

TIPS = (
    "Pair water with a habit you already have — one glass after waking is an easy win.",
    "Keep your bottle within reach. Visibility is one of the strongest hydration cues.",
    "Sip steadily through the day instead of trying to catch up all at once.",
    "Drink before meals and after movement to make hydration part of your rhythm.",
    "A reusable bottle with volume marks makes every refill easier to count.",
    "Thirst can lag behind your needs during focused work — let reminders do the remembering.",
)

_SIP_GUARD_NOTICE_KEY = "home_sip_guard_notice"


def _log_amount(amount_ml: int, source: str) -> None:
    data = st.session_state.data
    before = progress_summary(data)["progress"]
    try:
        after = add_water(data, amount_ml, source=source)
    except WaterLogCooldownError as error:
        st.session_state[_SIP_GUARD_NOTICE_KEY] = {
            "remaining_seconds": error.retry_after_seconds,
        }
        # Never let a blocked repeat inherit success feedback in a direct page run.
        st.session_state.sound_event = None
        st.session_state.celebrate_once = False
        st.session_state.flash_message = None
        return

    st.session_state.pop(_SIP_GUARD_NOTICE_KEY, None)
    st.session_state.store.save(data)
    units = data.get("preferences", {}).get("units", "ml")
    st.session_state.flash_message = (
        f"{format_volume(amount_ml, units)} added to today."
    )
    if before < 1 <= after["progress"]:
        st.session_state.celebrate_once = True
        st.session_state.sound_event = "goal"
    else:
        st.session_state.sound_event = "water"


def _render_sip_guard_notice(data: dict) -> None:
    """Show a persistent quick-log warning until the technical guard expires."""

    if not st.session_state.get(_SIP_GUARD_NOTICE_KEY, False):
        return

    remaining_seconds = water_log_cooldown_remaining(data)
    if remaining_seconds <= 0:
        st.session_state.pop(_SIP_GUARD_NOTICE_KEY, None)
        return

    unit = "second" if remaining_seconds == 1 else "seconds"
    st.warning(
        "Sip Guard prevented a duplicate-looking quick log. "
        f"Try again in {remaining_seconds} {unit}; nothing was added.",
        icon=":material/shield:",
    )


def _progress_message(progress: float) -> str:
    if progress >= 1:
        return "Goal complete — brilliant work!"
    if progress >= 0.75:
        return "Final stretch — keep sipping steadily."
    if progress >= 0.5:
        return "Halfway there — steady progress."
    if progress >= 0.25:
        return "Good momentum — keep your bottle close."
    if progress > 0:
        return "First sips logged — keep the rhythm."
    return "Your first sip starts today’s progress."


def _expected_progress(wake_time: str, sleep_time: str) -> float:
    """Return how far through the user's waking window the current time is."""

    now = local_now()
    try:
        wake_hour, wake_minute = (int(part) for part in wake_time.split(":", 1))
        sleep_hour, sleep_minute = (int(part) for part in sleep_time.split(":", 1))
    except (AttributeError, TypeError, ValueError):
        wake_hour, wake_minute, sleep_hour, sleep_minute = 7, 0, 22, 0

    wake_total = wake_hour * 60 + wake_minute
    sleep_total = sleep_hour * 60 + sleep_minute
    now_total = now.hour * 60 + now.minute
    if sleep_total <= wake_total:
        sleep_total += 24 * 60
        if now_total < wake_total:
            now_total += 24 * 60
    window = max(1, sleep_total - wake_total)
    return max(0.0, min(1.0, (now_total - wake_total) / window))


def _suggested_next_sip(remaining_ml: int, expected_progress: float) -> int:
    """Return a gentle, bounded portion for the remaining waking-day plan."""

    if remaining_ml <= 0:
        return 0
    remaining_occasions = max(1, min(8, round((1 - expected_progress) * 8)))
    rounded = round((remaining_ml / remaining_occasions) / 50) * 50
    return max(50, min(500, rounded))


def _daily_tip(pet_name: str) -> None:
    """Render a stable daily tip without background reruns or visual churn."""

    tip_index = local_now().date().toordinal() % len(TIPS)
    st.info(TIPS[tip_index], icon=":material/lightbulb:")
    st.caption(f"Today’s tip from {pet_name}.")


data = st.session_state.data
profile = data.get("profile", {})
preferences = data.get("preferences", {})
summary = progress_summary(data)
units = preferences.get("units", "ml")
name = profile.get("name", "Hydration hero") or "Hydration hero"
pet = pet_snapshot(data)
pet_name = str(pet.get("name", "Ripple")) or "Ripple"
quick_amounts = preferences.get("quick_log_amounts_ml", (250, 500, 750, 1000))
if not isinstance(quick_amounts, (list, tuple)) or len(quick_amounts) != 4:
    quick_amounts = (250, 500, 750, 1000)
now = local_now()
greeting = "Good morning" if now.hour < 12 else "Good afternoon" if now.hour < 18 else "Good evening"

page_intro(
    "Your daily flow",
    f"{greeting}, {name}",
    "A calm place to log each sip, stay on pace, and make hydration feel effortless.",
    "Private & local",
)

if st.session_state.pop("celebrate_once", False) and summary["goal_met"]:
    celebration_confetti()
    st.success(
        f"Daily goal complete! {pet_name} unlocked a celebration for you.",
        icon=":material/celebration:",
    )

with st.container(
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
    gap="medium",
    key="home-overview-row",
):
    with st.container(border=True, key="today-progress-card", width=640):
        with st.container(
            horizontal=True,
            horizontal_alignment="distribute",
            vertical_alignment="center",
            key="today-progress-heading",
        ):
            st.subheader("Today’s hydration")
            st.badge(
                f"{summary['percentage']:.0f}% complete",
                icon=":material/water_drop:",
                color="blue" if summary["progress"] < 1 else "green",
            )

        st.markdown(
            f"## {format_volume(summary['intake_ml'], units)} "
            f":gray[/ {format_volume(summary['goal_ml'], units)}]"
        )
        st.progress(
            min(summary["progress"], 1.0),
            text=_progress_message(summary["progress"]),
        )

        with st.container(horizontal=True, key="today-metrics-row"):
            st.metric(
                "Remaining",
                format_volume(summary["remaining_ml"], units),
                border=True,
            )
            st.metric(
                "Current streak",
                f"{calculate_streak(data)} days",
                border=True,
            )
            recent_history = history_rows(data, days=7)
            weekly_values = [row.get("intake_ml", 0) for row in recent_history]
            weekly_average = int(sum(weekly_values) / max(1, len(weekly_values)))
            st.metric(
                "7-day average",
                format_volume(weekly_average, units),
                border=True,
                chart_data=weekly_values,
                chart_type="area",
            )

    with st.container(key="home-buddy-panel", width=380):
        render_hourly_pet(pet, summary["progress"], compact=True)

st.space("small")
with st.container(border=True, key="home-quick-log"):
    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        key="home-quick-log-heading",
    ):
        st.subheader("Quick log")
        st.caption("One tap, instantly saved")

    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        key="home-quick-log-actions",
    ):
        for amount in quick_amounts:
            amount = int(amount)
            st.button(
                f"+{format_volume(amount, units)}",
                key=f"home_quick_{amount}",
                icon=":material/add:",
                on_click=_log_amount,
                args=(amount, "Quick log"),
                width=160,
                type="primary" if amount == quick_amounts[0] else "secondary",
            )

    st.caption(
        ":material/shield: **Sip Guard:** A "
        f"{WATER_LOG_COOLDOWN_SECONDS}-second interval prevents accidental "
        "double-counting from repeat taps. It is a logging safeguard, not drinking advice."
    )
    _render_sip_guard_notice(data)

with st.container(
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
    gap="medium",
    key="home-pace-row",
):
    expected = _expected_progress(
        profile.get("wake_time", "07:00"),
        profile.get("sleep_time", "22:00"),
    )
    pace_delta = summary["progress"] - expected
    suggested_sip = _suggested_next_sip(summary["remaining_ml"], expected)
    with st.container(border=True, key="home-pace-card", width=640):
        st.subheader("Your hydration pace")
        if summary["progress"] >= 1:
            st.success("Today’s plan is complete.", icon=":material/check_circle:")
        elif pace_delta >= 0.08:
            st.success(
                f"You’re {abs(pace_delta) * 100:.0f}% ahead of pace.",
                icon=":material/trending_up:",
            )
        elif pace_delta <= -0.12:
            st.warning(
                f"You’re {abs(pace_delta) * 100:.0f}% behind pace. A small glass can help.",
                icon=":material/water_full:",
            )
        else:
            st.info("You’re on pace. Keep sipping steadily.", icon=":material/pace:")

        with st.container(horizontal=True):
            st.metric(
                "Expected by now",
                format_volume(round(summary["goal_ml"] * expected), units),
                border=True,
            )
            st.metric(
                "Gentle next step",
                (
                    format_volume(suggested_sip, units)
                    if suggested_sip
                    else "Follow your thirst"
                ),
                border=True,
            )
        st.caption(
            "Pacing spreads the remaining goal across your waking window; it is a habit cue, not medical advice."
        )

        st.markdown("**A tip for this moment**")
        _daily_tip(pet_name)

    with st.container(key="home-bottle-panel", width=380):
        render_bottle(
            summary["progress"],
            summary["intake_ml"],
            summary["goal_ml"],
            units,
        )

recent_entries = list(reversed(summary.get("entries", [])))[:4]
with st.container(border=True):
    with st.container(
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
        key="home-flow-heading",
    ):
        st.subheader("Today’s flow")
        st.caption(f"{len(summary.get('entries', []))} logs today")

    if recent_entries:
        for index, entry in enumerate(recent_entries):
            raw_time = str(entry.get("logged_at", ""))
            try:
                logged_moment = datetime.fromisoformat(raw_time)
                if logged_moment.tzinfo is not None:
                    logged_moment = logged_moment.astimezone(current_timezone())
                logged_time = logged_moment.strftime("%I:%M %p")
            except ValueError:
                logged_time = "Just now"
            source = str(entry.get("source", "Water")).strip() or "Water"
            with st.container(
                horizontal=True,
                horizontal_alignment="distribute",
                vertical_alignment="center",
                key=f"home-flow-entry-{index}",
            ):
                st.markdown(
                    ":material/water_drop: "
                    f"**{format_volume(int(entry.get('amount_ml', 0)), units)}**"
                )
                st.caption(source)
                st.caption(logged_time)
    else:
        st.caption("No water logged yet. Tap a quick amount to start today’s timeline.")

if summary["progress"] >= 1:
    with st.container(border=True, key="daily-summary-card"):
        st.subheader("Today’s win", anchor=False)
        st.write(
            f"You reached **{format_volume(summary['intake_ml'], units)}** and completed "
            f"**{summary['percentage']:.0f}%** of your goal. Every extra sip still counts, "
            "but there is no need to race beyond what feels comfortable."
        )
