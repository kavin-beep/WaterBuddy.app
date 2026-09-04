"""Hydration trends and adherence insights."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from water_buddy.clock import current_timezone, local_date
from water_buddy.domain import calculate_streak, history_rows, progress_summary
from water_buddy.ui import (
    format_volume,
    mount_page_ambience,
    page_intro,
    render_empty_state,
)
from water_buddy.units import from_millilitres, unit_label

mount_page_ambience("insights")


def _as_date(value: Any) -> date:
    """Coerce persisted date-like values into a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return local_date()


def _number(row: Mapping[str, Any], *keys: str, default: float = 0) -> float:
    for key in keys:
        if key in row:
            try:
                return float(row[key])
            except (TypeError, ValueError):
                continue
    return default


def _optional_date(value: Any) -> date | None:
    """Return a persisted date when valid without inventing a fallback day."""

    if isinstance(value, datetime):
        return (
            value.astimezone(current_timezone()).date()
            if value.tzinfo is not None
            else value.date()
        )
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _eligible_history_days(
    app_data: Mapping[str, Any],
    requested_days: int,
    today: date,
) -> int:
    """Clamp a history window so it never predates this local account."""

    metadata = app_data.get("metadata", {})
    metadata = metadata if isinstance(metadata, Mapping) else {}
    created_date = _optional_date(metadata.get("created_at"))
    if created_date is None:
        return requested_days
    account_age_days = max(1, (today - created_date).days + 1)
    return min(requested_days, account_age_days)


data = st.session_state["data"]
units = str(data.get("preferences", {}).get("units", "ml"))
display_unit = unit_label(units)
is_light_theme = (
    str(data.get("preferences", {}).get("theme", "Dark")).casefold() == "light"
)

page_intro(
    "Insights",
    "See the rhythm behind every sip",
    "Compare intake with your daily target, spot consistent weeks, and learn where a small habit can make the biggest difference.",
    "Stored on this device",
)

window_days = st.segmented_control(
    "History range",
    options=[7, 14, 30],
    default=7,
    required=True,
    format_func=lambda days: f"{days} days",
    key="insights_window",
    width="stretch",
)
window_days = int(window_days or 7)

today = progress_summary(data)
fallback_goal = _number(today, "goal_ml", "goal", default=2200)
local_today = local_date()
eligible_days = _eligible_history_days(data, window_days, local_today)
raw_rows = history_rows(data, eligible_days, today=local_today)
normalized: list[dict[str, Any]] = []
has_hydration_activity = False

for raw_row in raw_rows:
    if not isinstance(raw_row, Mapping):
        continue
    row_date = _as_date(raw_row.get("date", raw_row.get("day")))
    intake_ml = max(0.0, _number(raw_row, "intake_ml", "intake", "total_ml"))
    entries_count = max(0.0, _number(raw_row, "entries_count"))
    has_hydration_activity = bool(
        has_hydration_activity or intake_ml > 0 or entries_count > 0
    )
    goal_ml = max(
        1.0,
        _number(raw_row, "goal_ml", "goal", "target_ml", default=fallback_goal),
    )
    adherence = min(intake_ml / goal_ml, 1.0)
    normalized.append(
        {
            "date": row_date,
            "intake_ml": round(intake_ml),
            "goal_ml": round(goal_ml),
            "adherence": adherence,
            "goal_met": intake_ml >= goal_ml,
        }
    )

normalized.sort(key=lambda row: row["date"])

if not normalized or not has_hydration_activity:
    render_empty_state(
        "Your trends will appear here",
        "Log your first drink on the home page, then return to see intake, goals, and consistency over time.",
        "query_stats",
    )
    st.stop()

average_intake = sum(row["intake_ml"] for row in normalized) / len(normalized)
total_intake = sum(row["intake_ml"] for row in normalized)
goal_days = sum(row["goal_met"] for row in normalized)
adherence_rate = goal_days / len(normalized)
streak = calculate_streak(data)
best_day = max(normalized, key=lambda row: row["intake_ml"])

with st.container(horizontal=True):
    st.metric(
        "Daily average",
        format_volume(round(average_intake), units),
        border=True,
        chart_data=[from_millilitres(row["intake_ml"], units) for row in normalized],
        chart_type="area",
    )
    st.metric(
        "Goals reached",
        f"{goal_days} of {len(normalized)}",
        f"{adherence_rate:.0%} adherence",
        border=True,
    )
    st.metric(
        "Total logged",
        format_volume(round(total_intake), units),
        border=True,
    )
    st.metric(
        "Current streak",
        f"{streak} day{'s' if streak != 1 else ''}",
        border=True,
    )

chart_frame = pd.DataFrame(normalized)
chart_frame["date"] = pd.to_datetime(chart_frame["date"])
chart_frame = chart_frame.rename(
    columns={"intake_ml": "Actual", "goal_ml": "Goal"}
)
for column in ("Actual", "Goal"):
    chart_frame[column] = chart_frame[column].map(
        lambda value: from_millilitres(value, units)
    )
chart_long = chart_frame.melt(
    id_vars=["date"],
    value_vars=["Actual", "Goal"],
    var_name="Series",
    value_name="Volume",
)

with st.container(border=True):
    st.subheader("Actual intake vs goal")
    st.caption(
        f"Your strongest day was {best_day['date'].strftime('%A, %d %b')} at "
        f"{format_volume(int(best_day['intake_ml']), units)}."
    )
    trend_chart = (
        alt.Chart(chart_long)
        .mark_line(point=alt.OverlayMarkDef(size=70), strokeWidth=3)
        .encode(
            x=alt.X("date:T", title=None, axis=alt.Axis(format="%d %b")),
            y=alt.Y(
                "Volume:Q",
                title=f"Volume ({display_unit})",
                scale=alt.Scale(zero=True),
            ),
            color=alt.Color(
                "Series:N",
                scale=alt.Scale(
                    domain=["Actual", "Goal"],
                    range=(
                        ["#0E7490", "#4338CA"]
                        if is_light_theme
                        else ["#22D3EE", "#A5B4FC"]
                    ),
                ),
                legend=alt.Legend(orient="top", title=None),
            ),
            strokeDash=alt.StrokeDash(
                "Series:N",
                scale=alt.Scale(domain=["Actual", "Goal"], range=[[1, 0], [7, 5]]),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("date:T", title="Date", format="%A, %d %b"),
                alt.Tooltip("Series:N", title="Measure"),
                alt.Tooltip(
                    "Volume:Q",
                    title=f"Volume ({display_unit})",
                    format=",.1f" if display_unit == "fl oz" else ",.0f",
                ),
            ],
        )
        .properties(height=330)
        .interactive(bind_y=False)
    )
    st.altair_chart(trend_chart)

calendar_frame = pd.DataFrame(normalized)
calendar_frame["date"] = pd.to_datetime(calendar_frame["date"])
calendar_frame["weekday"] = calendar_frame["date"].dt.day_name().str[:3]
calendar_frame["week_start"] = calendar_frame["date"] - pd.to_timedelta(
    calendar_frame["date"].dt.weekday, unit="D"
)
calendar_frame["week"] = calendar_frame["week_start"].dt.strftime("Week of %d %b")
calendar_frame["adherence_pct"] = (calendar_frame["adherence"] * 100).round()
calendar_frame["label"] = calendar_frame["adherence_pct"].map(lambda value: f"{value:.0f}%")
calendar_frame["intake_display"] = calendar_frame["intake_ml"].map(
    lambda value: from_millilitres(value, units)
)
calendar_frame["goal_display"] = calendar_frame["goal_ml"].map(
    lambda value: from_millilitres(value, units)
)

with st.container(border=True):
    st.subheader("Consistency calendar")
    st.caption("Each tile shows how much of that day's goal you completed.")
    weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    calendar_base = alt.Chart(calendar_frame).encode(
        x=alt.X("weekday:N", title=None, sort=weekday_order),
        y=alt.Y("week:N", title=None, sort=alt.SortOrder("descending")),
    )
    tiles = calendar_base.mark_rect(cornerRadius=8, stroke="#0E7490", strokeWidth=0.5).encode(
        color=alt.Color(
            "adherence_pct:Q",
            title="Goal complete",
            scale=alt.Scale(
                domain=[0, 100],
                range=(
                    ["#E6FFFB", "#0F766E"]
                    if is_light_theme
                    else ["#102A36", "#0F766E"]
                ),
            ),
            legend=alt.Legend(format=".0f"),
        ),
        tooltip=[
            alt.Tooltip("date:T", title="Date", format="%A, %d %b"),
            alt.Tooltip(
                "intake_display:Q",
                title=f"Intake ({display_unit})",
                format=",.1f" if display_unit == "fl oz" else ",.0f",
            ),
            alt.Tooltip(
                "goal_display:Q",
                title=f"Goal ({display_unit})",
                format=",.1f" if display_unit == "fl oz" else ",.0f",
            ),
            alt.Tooltip("adherence_pct:Q", title="Complete", format=".0f"),
        ],
    )
    labels = calendar_base.mark_text(fontSize=12, fontWeight=600).encode(
        text="label:N",
        color=alt.condition(
            alt.datum.adherence_pct >= 90,
            alt.value("white"),
            alt.value("#030817" if is_light_theme else "white"),
        ),
    )
    calendar_height = max(90, calendar_frame["week"].nunique() * 58)
    st.altair_chart((tiles + labels).properties(height=calendar_height))

with st.expander("View daily details", icon=":material/table_chart:"):
    details = pd.DataFrame(
        {
            "Date": [row["date"] for row in normalized],
            "Intake": [from_millilitres(row["intake_ml"], units) for row in normalized],
            "Goal": [from_millilitres(row["goal_ml"], units) for row in normalized],
            "Adherence": [row["adherence"] for row in normalized],
            "Status": ["Goal reached" if row["goal_met"] else "In progress" for row in normalized],
        }
    )
    st.dataframe(
        details,
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(format="ddd, DD MMM"),
            "Intake": st.column_config.NumberColumn(
                format="%.1f fl oz" if display_unit == "fl oz" else "%d ml"
            ),
            "Goal": st.column_config.NumberColumn(
                format="%.1f fl oz" if display_unit == "fl oz" else "%d ml"
            ),
            "Adherence": st.column_config.ProgressColumn(
                min_value=0,
                max_value=1,
                format="percent",
            ),
        },
    )
