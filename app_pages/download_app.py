"""Public WaterBuddy download page for the Windows desktop shortcut."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from water_buddy.ui import mount_page_ambience, page_intro, render_brand
from water_buddy.windows_download import build_windows_bundle

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRECTORY = ROOT / "assets" / "windows_app"

mount_page_ambience("welcome")
render_brand()
st.space("small")
page_intro(
    "WATERBUDDY FOR WINDOWS",
    "Keep WaterBuddy one click away.",
    "Add the WaterBuddy icon to your Windows Desktop and open the app in a clean Chrome window.",
    "No admin access needed",
)

visual, download = st.columns([0.7, 1.3], gap="large", vertical_alignment="center")
with visual:
    st.image(str(ASSET_DIRECTORY / "waterbuddy-icon.png"), width=190)

with download:
    st.subheader("Install in under a minute", anchor=False)
    st.markdown(
        "1. Download and extract the ZIP file.\n"
        "2. Double-click **Install WaterBuddy.cmd**.\n"
        "3. Open **WaterBuddy** from your Windows Desktop."
    )
    st.download_button(
        "Download WaterBuddy for Windows",
        data=build_windows_bundle(ASSET_DIRECTORY),
        file_name="WaterBuddy-Windows.zip",
        mime="application/zip",
        icon=":material/download:",
        type="primary",
        width="stretch",
    )

st.info(
    "The installer only creates a Desktop shortcut and copies its icon. It does not need administrator access, add a startup item, or store your password.",
    icon=":material/security:",
)
st.caption(
    "Chrome opens WaterBuddy in app mode. If Chrome is unavailable, the shortcut opens your default browser. Your remembered-device login continues to work in the same browser profile."
)
st.link_button(
    "Back to WaterBuddy",
    "https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/",
    icon=":material/arrow_back:",
)
