"""Compact pet launcher designed for a Windows desktop web shortcut."""

from __future__ import annotations

import os

import streamlit as st

from water_buddy.domain import WaterLogCooldownError, add_water, progress_summary
from water_buddy.pet import pet_snapshot
from water_buddy.ui import format_volume, mount_page_ambience, render_pet

mount_page_ambience("pet")

DEFAULT_APP_URL = "https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app"


def _log_from_desktop(amount_ml: int) -> None:
    data = st.session_state.data
    try:
        summary = add_water(data, amount_ml, source="Desktop pet")
    except WaterLogCooldownError as error:
        st.session_state.desktop_pet_notice = (
            "Sip Guard prevented a duplicate log. "
            f"Try again in {error.retry_after_seconds} seconds."
        )
        return

    st.session_state.store.save(data)
    units = data.get("preferences", {}).get("units", "ml")
    st.session_state.desktop_pet_notice = (
        f"{format_volume(amount_ml, units)} added — "
        f"today is now {summary['percentage']:.0f}% complete."
    )
    st.session_state.sound_event = "water"


data = st.session_state.data
preferences = data.get("preferences", {})
units = preferences.get("units", "ml")
quick_amounts = preferences.get("quick_log_amounts_ml", (250, 500, 750, 1000))
if not isinstance(quick_amounts, (list, tuple)) or len(quick_amounts) != 4:
    quick_amounts = (250, 500, 750, 1000)
summary = progress_summary(data)
pet = pet_snapshot(data)
pet["speech"] = "Pick a glass and I’ll add it to today’s Water Buddy progress."

st.title("Desktop pet", anchor=False)
st.caption("A compact one-click Water Buddy panel for Windows.")
render_pet(pet, summary["progress"], compact=True)

st.progress(
    min(summary["progress"], 1.0),
    text=(
        f"{format_volume(summary['intake_ml'], units)} of "
        f"{format_volume(summary['goal_ml'], units)}"
    ),
)

with st.container(border=True):
    st.subheader("Quick water log", anchor=False)
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        for amount in quick_amounts:
            safe_amount = int(amount)
            st.button(
                f"+{format_volume(safe_amount, units)}",
                key=f"desktop_pet_log_{safe_amount}",
                icon=":material/water_drop:",
                type="primary" if safe_amount == int(quick_amounts[0]) else "secondary",
                on_click=_log_from_desktop,
                args=(safe_amount,),
            )

notice = st.session_state.pop("desktop_pet_notice", None)
if notice:
    st.success(notice, icon=":material/check_circle:")

app_url = os.environ.get("WATER_BUDDY_APP_URL", DEFAULT_APP_URL).rstrip("/")
shortcut = (
    "[InternetShortcut]\r\n"
    f"URL={app_url}/desktop\r\n"
    "IconIndex=0\r\n"
)
st.download_button(
    "Download Windows desktop pet shortcut",
    data=shortcut.encode("utf-8"),
    file_name="WaterBuddy Pet.url",
    mime="application/internet-shortcut",
    icon=":material/install_desktop:",
    width="stretch",
)
st.caption(
    "Move the downloaded shortcut onto your Windows Desktop. Clicking it opens "
    "this pet panel with your four saved quick-log amounts."
)
