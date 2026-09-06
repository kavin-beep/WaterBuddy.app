"""Browser-cookie support for remembered-device authentication."""

from __future__ import annotations

from streamlit_cookies_manager import CookieManager

COOKIE_NAME = "device_session"
COOKIE_PREFIX = "waterbuddy.app/v1/"


def load_device_cookies() -> CookieManager:
    """Mount the bidirectional browser component and return its cookie mapping."""

    return CookieManager(prefix=COOKIE_PREFIX, path="/")


def set_device_cookie(cookies: CookieManager, token: str) -> bool:
    """Persist an opaque remembered-device token when the component is ready."""

    if not cookies.ready():
        return False
    cookies[COOKIE_NAME] = str(token)
    cookies.save()
    return True


def clear_device_cookie(cookies: CookieManager) -> bool:
    """Remove Water Buddy's remembered-device cookie from this browser."""

    if not cookies.ready():
        return False
    if COOKIE_NAME in cookies:
        del cookies[COOKIE_NAME]
        cookies.save()
    return True
