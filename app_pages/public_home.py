"""Public Water Buddy home with an obvious route into authentication."""

from __future__ import annotations

import streamlit as st

from water_buddy.ui import mount_page_ambience, render_brand, render_pet

mount_page_ambience("welcome")

render_brand()
st.space("medium")

intro, buddy = st.columns([1.15, 0.85], gap="large", vertical_alignment="center")
with intro:
    st.caption(":material/water_drop: YOUR DAILY HYDRATION COMPANION")
    st.title("Small sips. Stronger habits. One happy buddy.")
    st.write(
        "Track water, stay on pace with your own schedule, and grow a tiny "
        "companion as your hydration streak builds."
    )
    st.page_link(
        "app_pages/login.py",
        label="Sign in / Quick Login",
        icon=":material/login:",
        width="stretch",
    )
    st.page_link(
        "app_pages/download_app.py",
        label="Get the Windows app",
        icon=":material/download:",
        width="stretch",
    )
    st.caption(
        "Already remembered on this device? Water Buddy will take you straight "
        "to your private Home automatically."
    )

with buddy:
    render_pet(
        {
            "name": "Ripple",
            "level": 4,
            "xp": 68,
            "xp_to_next": 100,
            "stage": "Little ripple",
            "stage_index": 2,
            "energy": 86,
            "happiness": 94,
            "mood": "curious",
            "speech": "Sign in and I will keep your hydration journey ready.",
            "equipped_accessory": "leaf",
        },
        0.72,
        compact=True,
    )

st.space("medium")
with st.container(horizontal=True, gap="medium"):
    with st.container(border=True):
        st.subheader("Quick logging", anchor=False)
        st.caption("Record a glass in one tap and see today’s progress instantly.")
    with st.container(border=True):
        st.subheader("Personal timing", anchor=False)
        st.caption("Reminders follow the timezone and schedule set by the user.")
    with st.container(border=True):
        st.subheader("Private profiles", anchor=False)
        st.caption("Each account keeps its own hydration history and preferences.")
