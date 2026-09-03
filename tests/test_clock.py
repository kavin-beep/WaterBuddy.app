"""Tests for Water Buddy's application timezone."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from water_buddy.clock import APP_TIMEZONE, local_now


class ApplicationClockTests(unittest.TestCase):
    def test_utc_moment_converts_to_india_standard_time(self) -> None:
        utc_moment = datetime(2026, 9, 3, 4, 30, tzinfo=timezone.utc)

        self.assertEqual(local_now(utc_moment), datetime(2026, 9, 3, 10, 0))
        self.assertEqual(APP_TIMEZONE.utcoffset(None).total_seconds(), 19_800)

    def test_naive_persisted_time_remains_unchanged(self) -> None:
        persisted = datetime(2026, 9, 3, 10, 0)

        self.assertEqual(local_now(persisted), persisted)


if __name__ == "__main__":
    unittest.main()
