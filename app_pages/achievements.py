"""Achievement badges, milestones, and weekly hydration challenge."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from water_buddy.domain import (
    badge_catalog,
    calculate_streak,
    calendar_week_rows,
    history_rows,
    hydration_score,
    unlocked_badges,
)
from water_buddy.pet import pet_snapshot
from water_buddy.ui import (
    format_volume,
    mount_page_ambience,
    page_intro,
    render_badge_card,
    render_pet,
)

mount_page_ambience("achievements")

BADGE_CATALOG = badge_catalog()
STREAK_MILESTONES = (3, 7, 14, 30, 60, 100)
GOAL_DAY_MILESTONES = (1, 3, 7, 14, 30)
VOLUME_MILESTONES_ML = (10_000, 25_000, 50_000, 100_000)


def _score_value(value: Any) -> int:
    if isinstance(value, Mapping):
        value = value.get("score", value.get("value", 0))
    try:
        return max(0, min(100, round(float(value))))
    except (TypeError, ValueError):
        return 0


def _history_number(row: Mapping[str, Any], *keys: str) -> float:
    for key in keys:
        if key not in row:
            continue
        try:
            return float(row[key])
        except (TypeError, ValueError):
            continue
    return 0


data = st.session_state["data"]
units = str(data.get("preferences", {}).get("units", "ml"))
score = _score_value(hydration_score(data))
streak = max(0, int(calculate_streak(data)))
history = [row for row in history_rows(data, 30) if isinstance(row, Mapping)]
goal_days = sum(
    _history_number(row, "intake_ml", "intake", "total_ml")
    >= max(1, _history_number(row, "goal_ml", "goal", "target_ml"))
    for row in history
)
recent_intake = sum(
    max(0, _history_number(row, "intake_ml", "intake", "total_ml"))
    for row in history
)
daily_records = data.get("daily_records", {})
record_values = daily_records.values() if isinstance(daily_records, Mapping) else []
journey_records = [record for record in record_values if isinstance(record, Mapping)]
total_intake = (
    sum(max(0, _history_number(record, "intake_ml", "intake", "total_ml")) for record in journey_records)
    if journey_records
    else recent_intake
)
raw_unlocked = unlocked_badges(data)
raw_unlocked = list(raw_unlocked) if raw_unlocked else []
unlocked_ids = {str(badge.get("id", "")) for badge in raw_unlocked}

page_intro(
    "Achievements",
    "Small sips, visible momentum",
    "Celebrate the routines you have built and see the next milestones waiting on your hydration journey.",
    f"{len(raw_unlocked)} unlocked",
)

with st.container(horizontal=True):
    st.metric("Hydration score", f"{score}/100", border=True)
    st.metric(
        "Current streak",
        f"{streak} day{'s' if streak != 1 else ''}",
        border=True,
    )
    st.metric("Goal days", str(goal_days), "Last 30 days", border=True)
    st.metric("Journey volume", format_volume(round(total_intake), units), border=True)

hero_left, hero_right = st.columns([1.35, 1], vertical_alignment="center")
with hero_left:
    with st.container(border=True):
        st.subheader("Your momentum")
        if score >= 85:
            momentum_message = "Excellent consistency. Protect the routine that got you here."
        elif score >= 60:
            momentum_message = "Your habit is taking shape. One steady week can lift your score further."
        elif score >= 30:
            momentum_message = "A promising start. Log each drink so every win counts."
        else:
            momentum_message = "Every hydration streak begins with one logged glass."
        st.write(momentum_message)
        st.progress(score / 100, text=f"Hydration score · {score}%")
with hero_right:
    achievement_pet = pet_snapshot(data)
    achievement_pet["speech"] = "Your effort is adding up."
    render_pet(achievement_pet, score / 100, compact=True)

st.subheader("Badge collection")
catalog_unlocked = unlocked_ids & {badge["id"] for badge in BADGE_CATALOG}

unlocked_tab, locked_tab = st.tabs(
    [
        f"Unlocked ({len(catalog_unlocked)})",
        f"Locked ({len(BADGE_CATALOG) - len(catalog_unlocked)})",
    ]
)
with unlocked_tab:
    unlocked_catalog = [
        badge for badge in BADGE_CATALOG if badge["id"] in catalog_unlocked
    ]
    if unlocked_catalog:
        for row_start in range(0, len(unlocked_catalog), 2):
            for column, badge in zip(st.columns(2), unlocked_catalog[row_start : row_start + 2]):
                with column:
                    render_badge_card(
                        badge["title"],
                        badge["description"],
                        True,
                        badge["accent"],
                    )
    else:
        with st.container(border=True):
            st.markdown(":material/lock_open: **Your first badge is close**")
            st.write("Log a drink to unlock First sip and begin your collection.")
with locked_tab:
    locked_catalog = [
        badge for badge in BADGE_CATALOG if badge["id"] not in catalog_unlocked
    ]
    if locked_catalog:
        for row_start in range(0, len(locked_catalog), 2):
            for column, badge in zip(st.columns(2), locked_catalog[row_start : row_start + 2]):
                with column:
                    render_badge_card(
                        badge["title"],
                        badge["description"],
                        False,
                        badge["accent"],
                    )
    else:
        st.success(
            "Every badge in this collection is unlocked. That is a remarkable routine.",
            icon=":material/stars:",
        )

st.subheader("What comes next")
next_streak = next(
    (target for target in STREAK_MILESTONES if target > streak),
    None,
)
next_goal_days = next(
    (target for target in GOAL_DAY_MILESTONES if target > goal_days),
    None,
)
next_volume = next(
    (target for target in VOLUME_MILESTONES_ML if target > total_intake),
    None,
)

milestone_columns = st.columns(3)
with milestone_columns[0].container(border=True, height="stretch"):
    st.markdown(":material/local_fire_department: **Streak milestone**")
    if next_streak is None:
        st.write("Every listed streak milestone is complete.")
        st.progress(1.0, text=f"{streak} days · top milestone reached")
        st.badge("Milestone set complete", icon=":material/check_circle:", color="green")
    else:
        streak_remaining = max(0, next_streak - streak)
        st.write(
            f"{streak_remaining} more goal day"
            f"{'s' if streak_remaining != 1 else ''} to reach {next_streak}."
        )
        st.progress(
            min(streak / next_streak, 1.0),
            text=f"{streak} / {next_streak} days",
        )
with milestone_columns[1].container(border=True, height="stretch"):
    st.markdown(":material/flag: **Goal-day milestone**")
    if next_goal_days is None:
        st.write("Every listed goal-day milestone is complete.")
        st.progress(1.0, text=f"{goal_days} goal days · top milestone reached")
        st.badge("Milestone set complete", icon=":material/check_circle:", color="green")
    else:
        goal_days_remaining = max(0, next_goal_days - goal_days)
        st.write(
            f"Reach your target on {goal_days_remaining} more day"
            f"{'s' if goal_days_remaining != 1 else ''}."
        )
        st.progress(
            min(goal_days / next_goal_days, 1.0),
            text=f"{goal_days} / {next_goal_days} days",
        )
with milestone_columns[2].container(border=True, height="stretch"):
    st.markdown(":material/water_full: **Volume milestone**")
    if next_volume is None:
        st.write("Every listed journey-volume milestone is complete.")
        st.progress(
            1.0,
            text=f"{format_volume(round(total_intake), units)} · top milestone reached",
        )
        st.badge("Milestone set complete", icon=":material/check_circle:", color="green")
    else:
        volume_remaining = max(0, round(next_volume - total_intake))
        st.write(
            f"Log {format_volume(volume_remaining, units)} more on your journey."
        )
        st.progress(
            min(total_intake / next_volume, 1.0),
            text=f"Toward {format_volume(next_volume, units)}",
        )

week = [row for row in calendar_week_rows(data) if isinstance(row, Mapping)]
weekly_goal_days = sum(
    _history_number(row, "intake_ml", "intake", "total_ml")
    >= max(1, _history_number(row, "goal_ml", "goal", "target_ml"))
    for row in week
)
challenge_target = 5
with st.container(border=True):
    st.subheader("Weekly challenge")
    st.markdown(":material/calendar_month: **Reach your goal on five days this week**")
    st.write(
        "Challenge complete—keep the tide rolling into next week."
        if weekly_goal_days >= challenge_target
        else f"{challenge_target - weekly_goal_days} more goal day{'s' if challenge_target - weekly_goal_days != 1 else ''} will complete this challenge."
    )
    st.progress(
        min(weekly_goal_days / challenge_target, 1.0),
        text=f"{min(weekly_goal_days, challenge_target)} of {challenge_target} goal days",
    )
    if weekly_goal_days >= challenge_target:
        st.badge("Challenge complete", icon=":material/check_circle:", color="green")
