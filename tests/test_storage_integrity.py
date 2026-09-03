"""Focused integrity tests for Water Buddy's atomic JSON store."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from water_buddy.domain import add_water, default_state, progress_summary
from water_buddy.storage import JsonStore, StorageError


class JsonStoreIntegrityTests(unittest.TestCase):
    def test_completed_goal_stays_complete_after_more_water_and_reload(self) -> None:
        goal_time = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)
        extra_time = goal_time + timedelta(minutes=1)
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "water_buddy.json")
            data = default_state(goal_time)
            goal_ml = progress_summary(data, now=goal_time)["goal_ml"]

            completed = add_water(data, goal_ml, now=goal_time)
            completed_at = completed["completed_at"]
            store.save(data)

            reloaded = store.load()
            add_water(reloaded, 250, now=extra_time)
            store.save(reloaded)
            final = progress_summary(store.load(), now=extra_time)

            self.assertGreater(final["progress"], 1)
            self.assertTrue(final["goal_met"])
            self.assertEqual(final["completed_at"], completed_at)

    def test_successful_save_refreshes_and_synchronizes_normalized_state(
        self,
    ) -> None:
        fixed_utc = datetime(2026, 8, 21, 8, 15, 30, tzinfo=timezone.utc)
        expected_updated_at = "2026-08-21T13:45:30"

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = default_state(datetime(2020, 1, 2, 9, 30, tzinfo=timezone.utc))
            data["profile"]["name"] = "  Ava  "
            data["metadata"]["updated_at"] = "2000-01-01T00:00:00"

            with patch("water_buddy.storage.local_now") as clock:
                clock.return_value = datetime.fromisoformat(expected_updated_at)
                store.save(data)

            primary = json.loads(path.read_text(encoding="utf-8"))
            backup = json.loads(store.backup_path.read_text(encoding="utf-8"))

            self.assertEqual(primary, backup)
            self.assertEqual(data, primary)
            self.assertEqual(data["profile"]["name"], "Ava")
            self.assertEqual(data["metadata"]["updated_at"], expected_updated_at)

    def test_backup_write_failure_resynchronizes_caller_to_committed_primary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            data["profile"]["name"] = "  Primary wins  "
            data["metadata"]["updated_at"] = "2000-01-01T00:00:00"
            atomic_replace = JsonStore._atomic_replace

            def interrupt_backup(target: Path, payload: str) -> None:
                if target == store.backup_path:
                    raise OSError("simulated backup interruption")
                atomic_replace(target, payload)

            with (
                patch.object(store, "_atomic_replace", interrupt_backup),
                self.assertRaises(StorageError),
            ):
                store.save(data)

            primary = json.loads(path.read_text(encoding="utf-8"))
            backup = json.loads(store.backup_path.read_text(encoding="utf-8"))

            self.assertEqual(data, primary)
            self.assertEqual(primary["profile"]["name"], "Primary wins")
            self.assertNotEqual(primary, backup)

    def test_backup_directory_is_rejected_before_primary_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            primary_before = path.read_bytes()
            persisted_before = json.loads(primary_before)
            store.backup_path.unlink()
            store.backup_path.mkdir()

            data["profile"]["name"] = "  Must not commit  "

            with (
                patch.object(
                    store,
                    "_atomic_replace",
                    wraps=store._atomic_replace,
                ) as atomic_replace,
                self.assertRaisesRegex(StorageError, "Backup path is not a file"),
            ):
                store.save(data)

            atomic_replace.assert_not_called()
            self.assertEqual(path.read_bytes(), primary_before)
            self.assertEqual(data, persisted_before)
            self.assertTrue(store.backup_path.is_dir())


if __name__ == "__main__":
    unittest.main()
