"""Per-session timezone helpers for Water Buddy."""

from __future__ import annotations

from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE_NAME = "UTC"

_current_timezone: ContextVar[tzinfo] = ContextVar(
    "water_buddy_timezone",
    default=timezone.utc,
)
_current_timezone_name: ContextVar[str] = ContextVar(
    "water_buddy_timezone_name",
    default=DEFAULT_TIMEZONE_NAME,
)
_current_browser_offset: ContextVar[int | None] = ContextVar(
    "water_buddy_browser_timezone_offset",
    default=None,
)


def _fixed_offset(browser_offset_minutes: object) -> tzinfo | None:
    """Convert JavaScript's UTC-minus-local offset into a Python timezone."""

    try:
        browser_offset = int(browser_offset_minutes)
    except (TypeError, ValueError, OverflowError):
        return None
    local_offset = -browser_offset
    if not -14 * 60 <= local_offset <= 14 * 60:
        return None
    sign = "+" if local_offset >= 0 else "-"
    absolute = abs(local_offset)
    label = f"UTC{sign}{absolute // 60:02d}:{absolute % 60:02d}"
    return timezone(timedelta(minutes=local_offset), name=label)


def configure_timezone(
    timezone_name: object = None,
    browser_offset_minutes: object = None,
) -> str:
    """Configure the clock for the current Streamlit/browser session.

    ``timezone_name`` should be the IANA name reported by
    ``st.context.timezone``. The browser offset is retained as a portable
    fallback for systems that do not ship an IANA timezone database.
    """

    requested_name = str(timezone_name or "").strip()
    selected: tzinfo | None = None
    selected_name = requested_name
    if requested_name:
        try:
            selected = ZoneInfo(requested_name)
        except (ZoneInfoNotFoundError, ValueError):
            selected = None

    try:
        parsed_browser_offset = int(browser_offset_minutes)
    except (TypeError, ValueError, OverflowError):
        parsed_browser_offset = None

    if selected is None:
        selected = _fixed_offset(parsed_browser_offset)
        selected_name = str(selected) if selected is not None else DEFAULT_TIMEZONE_NAME
    if selected is None:
        selected = timezone.utc

    _current_timezone.set(selected)
    _current_timezone_name.set(selected_name or DEFAULT_TIMEZONE_NAME)
    _current_browser_offset.set(parsed_browser_offset)
    return _current_timezone_name.get()


def current_timezone() -> tzinfo:
    """Return the timezone configured for the current user session."""

    return _current_timezone.get()


def current_timezone_name() -> str:
    """Return the browser timezone name, or a safe offset/UTC fallback."""

    return _current_timezone_name.get()


def current_browser_offset_minutes() -> int | None:
    """Return the browser's UTC-minus-local offset when it was supplied."""

    return _current_browser_offset.get()


def local_now(value: datetime | None = None) -> datetime:
    """Return a timezone-naive moment in the current user's local timezone.

    Water Buddy's existing JSON schema stores local wall-clock values without
    timezone metadata. Naive persisted values therefore remain unchanged,
    while aware values are converted for display in the active user timezone.
    """

    user_timezone = current_timezone()
    if value is None:
        current = datetime.now(user_timezone)
    elif value.tzinfo is not None:
        current = value.astimezone(user_timezone)
    else:
        current = value
    return current.replace(tzinfo=None, microsecond=0)


def local_date() -> date:
    """Return today's date in the current user's local timezone."""

    return datetime.now(current_timezone()).date()
