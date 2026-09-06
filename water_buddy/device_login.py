"""Small browser-cookie bridge for remembered-device authentication."""

from __future__ import annotations

import json

import streamlit.components.v1 as components

COOKIE_NAME = "water_buddy_device"
COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def set_device_cookie(token: str) -> None:
    """Persist an opaque token in a same-site, HTTPS-only browser cookie."""

    safe_token = json.dumps(str(token))
    components.html(
        f"""
        <script>
          document.cookie = {json.dumps(COOKIE_NAME + "=")} + encodeURIComponent({safe_token})
            + "; Path=/; Max-Age={COOKIE_MAX_AGE_SECONDS}; SameSite=Lax; Secure";
        </script>
        """,
        height=0,
    )


def clear_device_cookie() -> None:
    """Remove Water Buddy's remembered-device cookie in this browser."""

    components.html(
        f"""
        <script>
          document.cookie = {json.dumps(COOKIE_NAME + "=")}
            + "; Path=/; Max-Age=0; SameSite=Lax; Secure";
        </script>
        """,
        height=0,
    )
