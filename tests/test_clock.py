"""Tests for Water Buddy's per-user application timezone."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from water_buddy.clock import (
    configure_timezone,
    current_browser_offset_minutes,
    current_timezone_name,
    local_now,
)


class ApplicationClockTests(unittest.TestCase):
    def setUp(self) -> None:
        configure_timezone("UTC", 0)

    def test_utc_moment_converts_to_user_device_timezone(self) -> None:
        configure_timezone("Asia/Kolkata", -330)
        utc_moment = datetime(2026, 9, 3, 4, 30, tzinfo=timezone.utc)

        self.assertEqual(local_now(utc_moment), datetime(2026, 9, 3, 10, 0))
        self.assertEqual(current_timezone_name(), "Asia/Kolkata")
        self.assertEqual(current_browser_offset_minutes(), -330)

    def test_browser_offset_is_used_when_timezone_name_is_unavailable(self) -> None:
        configure_timezone("Not/A_Real_Zone", 240)
        utc_moment = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(local_now(utc_moment), datetime(2026, 9, 3, 8, 0))
        self.assertEqual(current_timezone_name(), "UTC-04:00")

    def test_naive_persisted_time_remains_unchanged(self) -> None:
        configure_timezone("America/New_York", 240)
        persisted = datetime(2026, 9, 3, 10, 0)

        self.assertEqual(local_now(persisted), persisted)


if __name__ == "__main__":
    unittest.main()
