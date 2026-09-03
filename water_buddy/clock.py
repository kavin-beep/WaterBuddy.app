"""Application-wide India Standard Time helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

# Water Buddy is configured for the user's Asia/Calcutta timezone. India does
# not observe daylight-saving time, so this fixed UTC offset is portable even
# on Windows and minimal deployment images without an IANA timezone database.
APP_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")


def local_now(value: datetime | None = None) -> datetime:
    """Return a timezone-naive IST moment suitable for existing JSON data."""

    if value is None:
        current = datetime.now(APP_TIMEZONE)
    elif value.tzinfo is not None:
        current = value.astimezone(APP_TIMEZONE)
    else:
        current = value
    return current.replace(tzinfo=None, microsecond=0)


def local_date() -> date:
    """Return today's calendar date in IST."""

    return datetime.now(APP_TIMEZONE).date()
