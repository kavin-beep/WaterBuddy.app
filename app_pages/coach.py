"""Offline, context-aware hydration coach."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import streamlit as st

from water_buddy.domain import calculate_streak, progress_summary
from water_buddy.pet import pet_snapshot
from water_buddy.ui import format_volume, mount_page_ambience, page_intro, render_pet

mount_page_ambience("coach")

MAX_COACH_MESSAGES = 51


def _number(source: Mapping[str, Any], *keys: str, default: float = 0) -> float:
    for key in keys:
        if key in source:
            try:
                return float(source[key])
            except (TypeError, ValueError):
                continue
    return default


def _coach_reply(
    prompt: str,
    app_data: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> str:
    """Return a deterministic response from local hydration context and rules."""
    text = prompt.casefold()
    preferences = app_data.get("preferences", {})
    profile = app_data.get("profile", {})
    units = str(preferences.get("units", "ml"))
    intake = max(0, round(_number(summary, "intake_ml", "intake")))
    goal = max(1, round(_number(summary, "goal_ml", "goal", default=2200)))
    remaining = max(0, round(_number(summary, "remaining_ml", "remaining", default=goal - intake)))
    progress = _number(summary, "progress", default=intake / goal)
    if progress > 1.5:
        progress /= 100
    percentage = max(0, round(_number(summary, "percentage", default=progress * 100)))
    name = str(profile.get("name", "friend")).strip() or "friend"
    now = datetime.now()
    hours_left = max(1, 22 - now.hour)
    interval = int(preferences.get("reminder_interval_minutes", 45) or 45)
    reminders_on = bool(preferences.get("reminders_enabled", True))
    streak = max(0, int(calculate_streak(app_data)))

    if any(term in text for term in ["emergency", "faint", "confus", "chest pain", "seizure"]):
        return (
            "Those symptoms need real medical attention, not an app response. Contact local emergency services or a qualified clinician now."
        )
    if any(term in text for term in ["medical", "kidney", "heart condition", "pregnan", "medicine", "medication"]):
        return (
            "Water needs can change with health conditions, pregnancy, and medicines. I can show your Water Buddy plan, but a clinician should set a medically appropriate target."
        )
    if any(term in text for term in ["goal", "target", "how much"]):
        return (
            f"Your current goal is {format_volume(goal, units)}. You have logged "
            f"{format_volume(intake, units)}, so {format_volume(remaining, units)} remains today."
        )
    if any(term in text for term in ["left", "remaining", "progress", "summary"]):
        if remaining == 0:
            return f"You reached today's goal, {name}. Your dashboard shows {format_volume(intake, units)} logged—great steady work."
        return (
            f"You are {percentage}% of the way there with {format_volume(intake, units)} logged. "
            f"Another {format_volume(remaining, units)} completes today's goal."
        )
    if any(term in text for term in ["plan", "pace", "schedule", "spread"]):
        if remaining == 0:
            return "Your goal is complete. Keep listening to thirst and avoid forcing extra water just to raise the number."
        portions = min(6, max(2, hours_left))
        portion_ml = max(50, round(remaining / portions / 50) * 50)
        return (
            f"A comfortable plan is about {format_volume(portion_ml, units)} on {portions} occasions "
            f"across the next {hours_left} hour{'s' if hours_left != 1 else ''}. Sip steadily instead of catching up all at once."
        )
    if any(term in text for term in ["remind", "notification", "nudge"]):
        if reminders_on:
            return (
                f"Your in-app reminders are on every {interval} minutes. They work while the Water Buddy tab is active, and you can adjust quiet hours on the Reminders page."
            )
        return "Your reminders are paused. Open the Reminders page to enable a schedule and choose quiet hours."
    if any(term in text for term in ["exercise", "workout", "gym", "run", "sport"]):
        return (
            "For activity, start hydrated, take regular sips, and log what you drink afterward. Heat, duration, and sweat rate matter, so use thirst and professional guidance for intense sessions."
        )
    if any(term in text for term in ["hot", "heat", "weather", "outside"]):
        return (
            "Warm weather can raise fluid needs. Carry water, take shade breaks, sip regularly, and pay attention to thirst and how you feel."
        )
    if any(term in text for term in ["coffee", "tea", "caffeine"]):
        return (
            "Coffee and tea can contribute fluid, but plain water is an easy everyday choice. Log the water you intentionally drink and keep caffeine comfortable for you."
        )
    if any(term in text for term in ["streak", "motivat", "habit", "consistent"]):
        if streak:
            return (
                f"You have a {streak}-day streak. Protect it with one simple cue: take a drink after waking, with meals, or whenever you return to your desk."
            )
        return "Start with one repeatable cue—log a glass after waking. A streak grows from actions that are easy to repeat."
    if any(term in text for term in ["too much", "overdrink", "overhydrat", "safe"]):
        return (
            "More is not always better. Avoid forcing large amounts quickly, follow thirst, and use a clinician's advice if you have fluid restrictions or health concerns."
        )
    if any(term in text for term in ["hello", "hey", "hi "]) or text.strip() in {"hi", "hey"}:
        return (
            f"Hi {name}. I can check today's progress, make a simple sip plan, explain reminders, or help you protect your streak."
        )
    if remaining == 0:
        return (
            "Today's goal is already complete. I can still help with reminder settings, habit cues, or a quick look at your streak."
        )
    return (
        f"Based on today's local log, you have {format_volume(remaining, units)} left. "
        "Ask me to check your pace, make a sip plan, explain reminders, or help with consistency."
    )


data = st.session_state["data"]
summary = progress_summary(data)
units = str(data.get("preferences", {}).get("units", "ml"))
intake = max(0, round(_number(summary, "intake_ml", "intake")))
goal = max(1, round(_number(summary, "goal_ml", "goal", default=2200)))
remaining = max(0, round(_number(summary, "remaining_ml", "remaining", default=goal - intake)))
progress = _number(summary, "progress", default=intake / goal)
if progress > 1.5:
    progress /= 100
percentage = max(0, round(_number(summary, "percentage", default=progress * 100)))

page_intro(
    "Offline smart coach",
    "Practical guidance from your own progress",
    "FLOW uses a transparent, local rule engine to turn your Water Buddy data into useful next steps. No message leaves this app.",
    "Private and offline",
)

st.info(
    "FLOW runs entirely on this device using transparent coaching rules and your saved hydration context.",
    icon=":material/offline_bolt:",
)

context_column, mascot_column = st.columns([1.5, 1], vertical_alignment="center")
with context_column:
    with st.container(border=True):
        st.subheader("Today's context")
        with st.container(horizontal=True):
            st.metric("Logged", format_volume(intake, units), border=True)
            st.metric("Remaining", format_volume(remaining, units), border=True)
            st.metric("Progress", f"{percentage}%", border=True)
with mascot_column:
    coach_pet = pet_snapshot(data)
    coach_pet["speech"] = (
        "Goal complete—beautiful work."
        if remaining == 0
        else "Ask me for your next simple step."
    )
    render_pet(coach_pet, progress, compact=True)

initial_message = (
    "I'm FLOW's offline smart coach. I can read today's Water Buddy progress and offer rule-based tips about pacing, reminders, routines, and goals."
)
st.session_state.setdefault(
    "coach_messages",
    [{"role": "assistant", "content": initial_message}],
)
messages = st.session_state["coach_messages"]
if not isinstance(messages, list) or not messages:
    messages = [{"role": "assistant", "content": initial_message}]
    st.session_state["coach_messages"] = messages
elif len(messages) > MAX_COACH_MESSAGES:
    messages[:] = [messages[0], *messages[-(MAX_COACH_MESSAGES - 1) :]]

st.subheader("Chat with FLOW")
with st.container(horizontal=True, horizontal_alignment="right"):
    if st.button(
        "Clear chat",
        icon=":material/delete_sweep:",
        type="tertiary",
        key="coach_clear_chat",
    ):
        st.session_state["coach_messages"] = [
            {"role": "assistant", "content": initial_message}
        ]
        st.rerun()

suggestion_map = {
    ":material/speed: Check my pace": "Check my pace for the rest of today",
    ":material/water_drop: What is left?": "How much water is left today?",
    ":material/calendar_clock: Make a sip plan": "Make a simple sip plan for today",
    ":material/local_fire_department: Help my streak": "Help me protect my streak",
}
pending_prompt: str | None = None
if len(messages) <= 1:
    selected_suggestion = st.pills(
        "Suggested prompts",
        options=list(suggestion_map),
        label_visibility="collapsed",
        key="coach_suggestion",
    )
    if selected_suggestion:
        pending_prompt = suggestion_map[selected_suggestion]

for message in messages:
    if not isinstance(message, Mapping):
        continue
    role = "user" if message.get("role") == "user" else "assistant"
    avatar = None if role == "user" else ":material/water_drop:"
    with st.chat_message(role, avatar=avatar):
        st.write(str(message.get("content", "")))

typed_prompt = st.chat_input(
    "Ask about your goal, pace, reminders, or routine",
    key="coach_chat_input",
    submit_mode="disable",
)
if typed_prompt:
    pending_prompt = str(typed_prompt)

if pending_prompt and pending_prompt.strip():
    clean_prompt = pending_prompt.strip()[:1000]
    messages.append({"role": "user", "content": clean_prompt})
    with st.chat_message("user"):
        st.write(clean_prompt)

    response = _coach_reply(clean_prompt, data, summary)
    messages.append({"role": "assistant", "content": response})
    if len(messages) > MAX_COACH_MESSAGES:
        messages[:] = [messages[0], *messages[-(MAX_COACH_MESSAGES - 1) :]]
    with st.chat_message("assistant", avatar=":material/water_drop:"):
        st.write(response)

st.caption(
    "FLOW provides general habit support, not diagnosis or medical care. For medical or fluid-restriction questions, consult a qualified clinician."
)
