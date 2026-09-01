"""Regression tests for Water Buddy's pure logic and JSON persistence."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from water_buddy.domain import (
    APP_ID,
    DEFAULT_QUICK_LOG_AMOUNTS_ML,
    SCHEMA_VERSION,
    WATER_LOG_COOLDOWN_SECONDS,
    WaterLogCooldownError,
    add_water,
    badge_catalog,
    calculate_goal,
    calculate_streak,
    calendar_week_rows,
    default_state,
    delete_water_entry,
    dismiss_reminder,
    history_rows,
    hydration_score,
    normalize_state,
    progress_summary,
    reminder_is_due,
    reset_day,
    set_daily_goal,
    snooze_reminder,
    undo_last_water,
    unlocked_badges,
    update_water_entry,
    validate_backup_payload,
    water_log_cooldown_remaining,
)
from water_buddy.pet import pet_snapshot
from water_buddy.storage import JsonStore, StorageError


class GoalTests(unittest.TestCase):
    def test_age_and_occupation_goals(self) -> None:
        self.assertEqual(calculate_goal("Children (4–8)", "Office Worker"), 1200)
        self.assertEqual(calculate_goal("Adults (14–64)", "Athlete"), 2900)
        self.assertEqual(calculate_goal("Seniors (65+)", "Outdoor Worker"), 2300)
        self.assertEqual(calculate_goal("Teens (9–13)", "Student"), 1850)

    def test_custom_and_manual_goal_bounds(self) -> None:
        self.assertEqual(calculate_goal("Adults (14–64)", "Custom", 350), 2550)
        self.assertEqual(
            calculate_goal("Adults (14–64)", "Athlete", manual_goal_ml=3100),
            3100,
        )
        self.assertEqual(
            calculate_goal("Adults (14–64)", "Custom", -9999),
            1700,
        )

    def test_setting_daily_goal_reconciles_completion_and_metadata(self) -> None:
        now = datetime(2026, 8, 7, 9, 30)  # noqa: DTZ001 - explicit local app time
        data = default_state(now)
        record = data["daily_records"][now.date().isoformat()]
        record["intake_ml"] = 2000

        completed_at = now + timedelta(hours=1)
        lowered = set_daily_goal(data, 1800, now=completed_at)
        self.assertTrue(lowered["goal_met"])
        self.assertEqual(lowered["completed_at"], completed_at.isoformat())
        self.assertEqual(data["metadata"]["updated_at"], completed_at.isoformat())

        repeated_at = completed_at + timedelta(minutes=30)
        unchanged = set_daily_goal(data, 1800, now=repeated_at)
        self.assertEqual(unchanged["completed_at"], completed_at.isoformat())

        raised_at = completed_at + timedelta(hours=1)
        raised = set_daily_goal(data, 3000, now=raised_at)
        self.assertFalse(raised["goal_met"])
        self.assertIsNone(raised["completed_at"])
        self.assertEqual(data["metadata"]["updated_at"], raised_at.isoformat())

    def test_setting_daily_goal_rejects_invalid_canonical_values(self) -> None:
        now = datetime(2026, 8, 7, 9, 30)  # noqa: DTZ001 - explicit local app time
        data = default_state(now)
        original = copy.deepcopy(data)

        for invalid in (499, 8001, 2200.5, True, float("nan")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                set_daily_goal(data, invalid, now=now)
            self.assertEqual(data, original)


class SchemaTests(unittest.TestCase):
    def test_schema_v4_identifies_water_buddy_documents(self) -> None:
        state = default_state(datetime(2026, 8, 7, 9, 30))

        self.assertEqual(SCHEMA_VERSION, 4)
        self.assertEqual(state["metadata"]["schema_version"], 4)
        self.assertEqual(state["metadata"]["app_id"], APP_ID)

        legacy = copy.deepcopy(state)
        legacy["metadata"].pop("app_id")
        legacy["metadata"]["schema_version"] = 3
        normalized = validate_backup_payload(legacy, datetime(2026, 8, 7, 10, 0))
        self.assertEqual(normalized["metadata"]["app_id"], APP_ID)
        self.assertEqual(normalized["metadata"]["schema_version"], SCHEMA_VERSION)

    def test_backup_validator_accepts_flat_legacy_state(self) -> None:
        normalized = validate_backup_payload(
            {"goal": 1800, "intake": 600},
            datetime(2026, 8, 7, 10, 0),
        )

        record = normalized["daily_records"]["2026-08-07"]
        self.assertEqual(record["goal_ml"], 1800)
        self.assertEqual(record["intake_ml"], 600)

    def test_backup_validator_rejects_unrelated_or_unsupported_json(self) -> None:
        invalid_payloads = (
            None,
            [],
            {},
            {"hello": "world"},
            {"profile": {}, "preferences": "not-an-object"},
            {
                "profile": {"avatar": "x"},
                "preferences": {"language": "en"},
            },
            {
                "profile": {},
                "preferences": {},
                "metadata": {"app_id": "another_app", "schema_version": 4},
            },
            {
                "profile": {},
                "preferences": {},
                "metadata": {"app_id": APP_ID, "schema_version": SCHEMA_VERSION + 1},
            },
            {
                "profile": {},
                "preferences": {},
                "metadata": {"schema_version": SCHEMA_VERSION},
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_backup_payload(payload)


class PreferenceTests(unittest.TestCase):
    def test_new_experience_preferences_have_safe_defaults(self) -> None:
        preferences = default_state(datetime(2026, 8, 7, 9, 30))["preferences"]

        self.assertEqual(preferences["theme"], "Dark")
        self.assertTrue(preferences["background_motion"])
        self.assertTrue(preferences["sound_enabled"])
        self.assertEqual(preferences["interface_sound_volume"], "Balanced")
        self.assertEqual(
            preferences["quick_log_amounts_ml"],
            list(DEFAULT_QUICK_LOG_AMOUNTS_ML),
        )

    def test_experience_preferences_are_normalized(self) -> None:
        data = default_state(datetime(2026, 8, 7, 9, 30))
        data["preferences"].update(
            {
                "theme": "LIGHT",
                "background_motion": False,
                "sound_enabled": False,
                "interface_sound_volume": "vivid",
            }
        )

        preferences = normalize_state(data)["preferences"]
        self.assertEqual(preferences["theme"], "Light")
        self.assertFalse(preferences["background_motion"])
        self.assertFalse(preferences["sound_enabled"])
        self.assertEqual(preferences["interface_sound_volume"], "Vivid")

        data["preferences"]["theme"] = "sepia"
        data["preferences"]["interface_sound_volume"] = "maximum"
        preferences = normalize_state(data)["preferences"]
        self.assertEqual(preferences["theme"], "Dark")
        self.assertEqual(preferences["interface_sound_volume"], "Balanced")

    def test_display_units_and_persisted_booleans_are_canonicalized(self) -> None:
        now = datetime(2026, 8, 7, 9, 30)  # noqa: DTZ001 - explicit local app time
        data = default_state(now)
        data["preferences"].update(
            {
                "units": "  FLUID OUNCES  ",
                "background_motion": "false",
                "sound_enabled": "OFF",
                "reminders_enabled": "0",
            }
        )

        preferences = normalize_state(data, now)["preferences"]
        self.assertEqual(preferences["units"], "oz")
        self.assertFalse(preferences["background_motion"])
        self.assertFalse(preferences["sound_enabled"])
        self.assertFalse(preferences["reminders_enabled"])

        data["preferences"].update(
            {
                "units": "litres",
                "background_motion": "not-a-boolean",
                "sound_enabled": None,
                "reminders_enabled": [],
            }
        )
        preferences = normalize_state(data, now)["preferences"]
        self.assertEqual(preferences["units"], "ml")
        self.assertTrue(preferences["background_motion"])
        self.assertTrue(preferences["sound_enabled"])
        self.assertTrue(preferences["reminders_enabled"])

    def test_quick_log_amounts_are_safe_unique_and_always_have_four(self) -> None:
        data = default_state(datetime(2026, 8, 7, 9, 30))
        data["preferences"]["quick_log_amounts_ml"] = [
            300,
            "300",
            True,
            -1,
            6000,
            450.5,
            600,
            900,
        ]

        amounts = normalize_state(data)["preferences"]["quick_log_amounts_ml"]
        self.assertEqual(amounts, [300, 600, 900, 250])
        self.assertEqual(len(amounts), len(set(amounts)))
        self.assertTrue(all(1 <= amount <= 5000 for amount in amounts))


class LoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 9, 30)
        self.data = default_state(self.now)

    def test_add_undo_and_reset(self) -> None:
        starting_pet_xp = pet_snapshot(self.data, self.now)["xp"]
        summary = add_water(self.data, 500, "Bottle", self.now)
        self.assertEqual(summary["intake_ml"], 500)
        self.assertEqual(summary["remaining_ml"], 1700)
        self.assertAlmostEqual(summary["progress"], 500 / 2200)
        self.assertEqual(len(summary["entries"]), 1)
        self.assertGreater(pet_snapshot(self.data, self.now)["xp"], starting_pet_xp)

        self.assertTrue(undo_last_water(self.data, self.now.date()))
        self.assertEqual(progress_summary(self.data, self.now.date())["intake_ml"], 0)
        self.assertEqual(pet_snapshot(self.data, self.now)["xp"], starting_pet_xp)
        self.assertFalse(undo_last_water(self.data, self.now.date()))

        add_water(self.data, 250, now=self.now)
        self.assertGreater(pet_snapshot(self.data, self.now)["xp"], starting_pet_xp)
        reset_day(self.data, self.now.date())
        reset_summary = progress_summary(self.data, self.now.date())
        self.assertEqual(reset_summary["intake_ml"], 0)
        self.assertEqual(reset_summary["entries"], [])
        self.assertEqual(pet_snapshot(self.data, self.now)["xp"], starting_pet_xp)

    def test_goal_crossing_unlocks_badges(self) -> None:
        add_water(self.data, 2200, now=self.now)
        badge_ids = {badge["id"] for badge in unlocked_badges(self.data)}
        self.assertIn("first_sip", badge_ids)
        self.assertIn("goal_getter", badge_ids)
        self.assertEqual(progress_summary(self.data, self.now.date())["percentage"], 100)

    def test_invalid_amounts_are_rejected(self) -> None:
        for invalid in (0, -1, 5001, True, 250.5, "250.5", float("nan")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                add_water(self.data, invalid, now=self.now)

    def test_cooldown_blocks_at_29_seconds_and_allows_at_30(self) -> None:
        add_water(self.data, 250, source="Glass", now=self.now)

        almost_ready = self.now + timedelta(seconds=29)
        self.assertEqual(water_log_cooldown_remaining(self.data, almost_ready), 1)
        with self.assertRaises(WaterLogCooldownError) as caught:
            add_water(self.data, 500, source="Workout", now=almost_ready)
        self.assertEqual(caught.exception.retry_after_seconds, 1)
        self.assertEqual(str(caught.exception), caught.exception.user_message)
        self.assertIn("1 second", caught.exception.user_message)

        ready = self.now + timedelta(seconds=WATER_LOG_COOLDOWN_SECONDS)
        self.assertEqual(water_log_cooldown_remaining(self.data, ready), 0)
        summary = add_water(self.data, 500, source="Workout", now=ready)
        self.assertEqual(summary["intake_ml"], 750)

    def test_blocked_log_does_not_mutate_state_or_award_xp(self) -> None:
        add_water(self.data, 250, now=self.now)
        state_before_block = copy.deepcopy(self.data)
        xp_before_block = pet_snapshot(self.data, self.now)["xp"]

        with self.assertRaises(WaterLogCooldownError):
            add_water(
                self.data,
                2200,
                source="Different source",
                now=self.now + timedelta(seconds=1),
            )

        self.assertEqual(self.data, state_before_block)
        self.assertEqual(pet_snapshot(self.data, self.now)["xp"], xp_before_block)

    def test_malformed_and_other_day_entries_are_ignored(self) -> None:
        today_record = self.data["daily_records"][self.now.date().isoformat()]
        today_record["entries"] = [
            None,
            {"amount_ml": 250, "logged_at": "not-a-timestamp"},
            {"amount_ml": 0, "logged_at": self.now.isoformat()},
            {
                "amount_ml": 250,
                "logged_at": (self.now - timedelta(days=1)).isoformat(),
            },
        ]
        yesterday = self.now.date() - timedelta(days=1)
        self.data["daily_records"][yesterday.isoformat()] = {
            "goal_ml": 2200,
            "intake_ml": 250,
            "entries": [
                {"amount_ml": 250, "logged_at": self.now.isoformat()}
            ],
        }

        self.assertEqual(water_log_cooldown_remaining(self.data, self.now), 0)
        summary = add_water(self.data, 100, now=self.now)
        self.assertEqual(summary["intake_ml"], 100)

    def test_future_timestamp_retry_is_clamped_to_thirty_seconds(self) -> None:
        record = self.data["daily_records"][self.now.date().isoformat()]
        record["entries"] = [
            {
                "amount_ml": 250,
                "logged_at": (self.now + timedelta(hours=2)).isoformat(),
            }
        ]

        self.assertEqual(
            water_log_cooldown_remaining(self.data, self.now),
            WATER_LOG_COOLDOWN_SECONDS,
        )
        with self.assertRaises(WaterLogCooldownError) as caught:
            add_water(self.data, 250, now=self.now)
        self.assertEqual(
            caught.exception.retry_after_seconds,
            WATER_LOG_COOLDOWN_SECONDS,
        )

    def test_undo_and_reset_remove_the_active_cooldown(self) -> None:
        add_water(self.data, 250, now=self.now)
        self.assertGreater(water_log_cooldown_remaining(self.data, self.now), 0)
        self.assertTrue(undo_last_water(self.data, self.now.date()))
        self.assertEqual(water_log_cooldown_remaining(self.data, self.now), 0)

        add_water(self.data, 250, now=self.now)
        reset_day(self.data, self.now.date())
        self.assertEqual(water_log_cooldown_remaining(self.data, self.now), 0)
        summary = add_water(self.data, 250, now=self.now)
        self.assertEqual(summary["intake_ml"], 250)

    def test_update_and_delete_entry_preserve_identity_and_reverse_pet_xp(self) -> None:
        starting_xp = pet_snapshot(self.data, self.now)["xp"]
        added = add_water(self.data, 500, source="Bottle", now=self.now)
        entry = added["entries"][0]
        entry_id = entry["id"]
        logged_at = entry["logged_at"]
        edit_time = self.now + timedelta(minutes=1)

        updated = update_water_entry(
            self.data,
            entry_id,
            2200,
            source="Large bottle",
            now=edit_time,
        )

        self.assertEqual(updated["intake_ml"], 2200)
        self.assertTrue(updated["goal_met"])
        self.assertEqual(updated["completed_at"], edit_time.isoformat())
        self.assertEqual(updated["entries"][0]["id"], entry_id)
        self.assertEqual(updated["entries"][0]["logged_at"], logged_at)
        self.assertEqual(updated["entries"][0]["source"], "Large bottle")
        self.assertGreater(pet_snapshot(self.data, edit_time)["xp"], starting_xp)
        self.assertEqual(self.data["metadata"]["updated_at"], edit_time.isoformat())
        self.assertIn(
            "goal_getter",
            {badge["id"] for badge in unlocked_badges(self.data)},
        )

        delete_time = edit_time + timedelta(minutes=1)
        self.assertTrue(delete_water_entry(self.data, entry_id, now=delete_time))
        summary = progress_summary(self.data, delete_time.date())
        self.assertEqual(summary["intake_ml"], 0)
        self.assertEqual(summary["entries"], [])
        self.assertIsNone(summary["completed_at"])
        self.assertEqual(pet_snapshot(self.data, delete_time)["xp"], starting_xp)
        self.assertEqual(self.data["metadata"]["updated_at"], delete_time.isoformat())
        self.assertFalse(delete_water_entry(self.data, entry_id, now=delete_time))

    def test_entry_update_rejects_unknown_id_without_mutating_state(self) -> None:
        add_water(self.data, 250, now=self.now)
        before = copy.deepcopy(self.data)

        with self.assertRaises(KeyError):
            update_water_entry(
                self.data,
                "missing-entry",
                500,
                now=self.now + timedelta(minutes=1),
            )

        self.assertEqual(self.data, before)

    def test_normalization_reissues_duplicate_entry_ids(self) -> None:
        record = self.data["daily_records"][self.now.date().isoformat()]
        record["intake_ml"] = 750
        record["entries"] = [
            {
                "id": "duplicate-entry",
                "amount_ml": 250,
                "source": "Glass",
                "logged_at": self.now.isoformat(),
            },
            {
                "id": "duplicate-entry",
                "amount_ml": 500,
                "source": "Bottle",
                "logged_at": (self.now + timedelta(minutes=1)).isoformat(),
            },
        ]

        normalized = normalize_state(self.data, self.now)
        normalized_entries = normalized["daily_records"][
            self.now.date().isoformat()
        ]["entries"]
        normalized_ids = [entry["id"] for entry in normalized_entries]

        self.assertEqual(len(normalized_entries), 2)
        self.assertEqual(len(set(normalized_ids)), 2)
        self.assertEqual(normalized_ids[0], "duplicate-entry")


class BadgeTests(unittest.TestCase):
    def test_catalog_is_authoritative_canonical_and_isolated(self) -> None:
        expected_ids = [
            "first_sip",
            "goal_getter",
            "three_day_streak",
            "seven_day_streak",
            "ten_litres",
            "twenty_litres",
            "overachiever",
            "thirty_day_streak",
        ]
        catalog = badge_catalog()
        self.assertEqual([badge["id"] for badge in catalog], expected_ids)
        catalog[0]["title"] = "Changed by caller"
        self.assertEqual(badge_catalog()[0]["title"], "First sip")

        data = default_state(datetime(2026, 8, 7, 9, 30))
        data["achievements"] = ["daily_goal", *expected_ids]
        normalized = normalize_state(data, datetime(2026, 8, 7, 9, 30))
        self.assertNotIn("daily_goal", normalized["achievements"])
        self.assertEqual(
            [badge["id"] for badge in unlocked_badges(normalized)],
            expected_ids,
        )

    def test_page_milestones_are_derived_by_the_domain(self) -> None:
        now = datetime(2026, 8, 7, 9, 30)
        data = default_state(now)
        record = data["daily_records"][now.date().isoformat()]
        record["intake_ml"] = 20_000

        unlocked = {badge["id"] for badge in unlocked_badges(data)}
        self.assertIn("twenty_litres", unlocked)
        self.assertIn("overachiever", unlocked)


class HistoryTests(unittest.TestCase):
    def test_streak_history_and_score(self) -> None:
        today = date(2026, 8, 7)
        data = default_state(datetime.combine(today, datetime.min.time()))
        for offset in range(3):
            day = today - timedelta(days=offset)
            data["daily_records"][day.isoformat()] = {
                "goal_ml": 2000,
                "intake_ml": 2000,
                "entries": [],
                "completed_at": datetime.combine(day, datetime.min.time()).isoformat(),
                "reset_count": 0,
            }

        self.assertEqual(calculate_streak(data, today), 3)
        rows = history_rows(data, 7, today)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[-1]["date"], today.isoformat())
        self.assertTrue(rows[-1]["goal_met"])
        self.assertGreater(hydration_score(data, today), 0)

        badge_ids = {badge["id"] for badge in unlocked_badges(data)}
        self.assertIn("three_day_streak", badge_ids)

    def test_unfinished_today_does_not_break_yesterday_streak(self) -> None:
        today = date(2026, 8, 7)
        data = default_state(datetime.combine(today, datetime.min.time()))
        for offset in (1, 2):
            day = today - timedelta(days=offset)
            data["daily_records"][day.isoformat()] = {
                "goal_ml": 1800,
                "intake_ml": 1800,
                "entries": [],
                "completed_at": None,
                "reset_count": 0,
            }
        self.assertEqual(calculate_streak(data, today), 2)

    def test_new_successful_user_scores_only_their_eligible_day(self) -> None:
        today = date(2026, 8, 7)
        data = default_state(datetime(2026, 8, 7, 8, 0))
        record = data["daily_records"][today.isoformat()]
        record["intake_ml"] = record["goal_ml"]

        self.assertEqual(hydration_score(data, today), 100)

        data["metadata"]["created_at"] = "2026-08-05T08:00:00"
        self.assertEqual(hydration_score(data, today), 33)

    def test_calendar_week_rows_cover_monday_through_sunday(self) -> None:
        today = date(2026, 8, 7)  # Friday
        data = default_state(datetime(2026, 8, 7, 8, 0))
        monday = date(2026, 8, 3)
        data["daily_records"][monday.isoformat()] = {
            "goal_ml": 2000,
            "intake_ml": 1000,
            "entries": [],
            "completed_at": None,
            "reset_count": 0,
        }

        rows = calendar_week_rows(data, today)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["date"], "2026-08-03")
        self.assertEqual(rows[-1]["date"], "2026-08-09")
        self.assertEqual(rows[0]["intake_ml"], 1000)


class ReminderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 12, 0)
        self.data = default_state(self.now)

    def test_due_snooze_and_dismiss(self) -> None:
        self.data["preferences"]["next_reminder_at"] = (
            self.now - timedelta(minutes=1)
        ).isoformat()
        self.assertTrue(reminder_is_due(self.data, self.now))

        snooze_reminder(self.data, 10, self.now)
        self.assertFalse(reminder_is_due(self.data, self.now))
        self.assertEqual(
            datetime.fromisoformat(self.data["preferences"]["next_reminder_at"]),
            self.now + timedelta(minutes=10),
        )

        dismiss_reminder(self.data, self.now)
        self.assertEqual(
            datetime.fromisoformat(self.data["preferences"]["next_reminder_at"]),
            self.now + timedelta(minutes=45),
        )

    def test_quiet_hours_block_due_reminder(self) -> None:
        late = self.now.replace(hour=23)
        self.data["profile"]["sleep_time"] = "23:59"
        self.data["preferences"]["next_reminder_at"] = (
            late - timedelta(minutes=1)
        ).isoformat()
        self.assertFalse(reminder_is_due(self.data, late))

    def test_completed_daily_goal_blocks_due_reminder(self) -> None:
        record = self.data["daily_records"][self.now.date().isoformat()]
        record["intake_ml"] = record["goal_ml"]
        self.data["preferences"]["next_reminder_at"] = (
            self.now - timedelta(minutes=1)
        ).isoformat()

        self.assertFalse(reminder_is_due(self.data, self.now))


class StorageTests(unittest.TestCase):
    def test_initial_creation_and_save_keep_matching_atomic_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            created = store.load()

            self.assertTrue(store.backup_path.is_file())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                json.loads(store.backup_path.read_text(encoding="utf-8")),
            )
            self.assertEqual(created["metadata"]["app_id"], APP_ID)

            created["profile"]["name"] = "Ava"
            store.save(created)
            primary = json.loads(path.read_text(encoding="utf-8"))
            backup = json.loads(store.backup_path.read_text(encoding="utf-8"))
            self.assertEqual(primary, backup)
            self.assertEqual(backup["profile"]["name"], "Ava")

    def test_round_trip_and_corrupt_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            data["profile"]["name"] = "Ava"
            add_water(data, 250)
            store.save(data)

            loaded = JsonStore(path).load()
            self.assertEqual(loaded["profile"]["name"], "Ava")
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

            path.write_text("{not valid json", encoding="utf-8")
            recovered = store.load()
            self.assertEqual(recovered["profile"]["name"], "Ava")
            self.assertIsNotNone(store.last_recovery_path)
            self.assertTrue(store.last_recovery_path.is_file())
            self.assertEqual(
                store.last_recovery_path.read_text(encoding="utf-8"),
                "{not valid json",
            )
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["profile"]["name"],
                "Ava",
            )

            store.load()
            self.assertIsNone(store.last_recovery_path)

    def test_partial_backup_write_keeps_newer_primary_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            data["profile"]["name"] = "Newest profile"
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

            recovered = JsonStore(path).load()
            self.assertEqual(recovered["profile"]["name"], "Newest profile")
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                json.loads(store.backup_path.read_text(encoding="utf-8")),
            )

    def test_escaped_lone_surrogate_can_seed_and_round_trip_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            data = default_state()
            data["profile"]["legacy_extra"] = "\ud800"
            path.write_text(
                json.dumps(data, ensure_ascii=True),
                encoding="utf-8",
            )

            store = JsonStore(path)
            loaded = store.load()

            self.assertEqual(loaded["profile"]["legacy_extra"], "\ud800")
            self.assertTrue(store.backup_path.is_file())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                json.loads(store.backup_path.read_text(encoding="utf-8")),
            )

    def test_structurally_unrelated_primary_recovers_valid_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            data["profile"]["name"] = "Known good"
            store.save(data)
            path.write_text('{"totally": "unrelated"}', encoding="utf-8")

            recovered = store.load()

            self.assertEqual(recovered["profile"]["name"], "Known good")
            self.assertEqual(
                store.last_recovery_path.read_text(encoding="utf-8"),
                '{"totally": "unrelated"}',
            )

    def test_future_primary_schema_recovers_without_downgrading_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            data["profile"]["name"] = "Supported backup"
            store.save(data)
            unsupported = json.loads(path.read_text(encoding="utf-8"))
            unsupported["metadata"]["schema_version"] = SCHEMA_VERSION + 1
            path.write_text(json.dumps(unsupported), encoding="utf-8")

            recovered = store.load()

            self.assertEqual(recovered["profile"]["name"], "Supported backup")
            self.assertEqual(recovered["metadata"]["schema_version"], SCHEMA_VERSION)
            preserved = json.loads(
                store.last_recovery_path.read_text(encoding="utf-8")
            )
            self.assertEqual(
                preserved["metadata"]["schema_version"],
                SCHEMA_VERSION + 1,
            )

    def test_corrupt_primary_and_backup_preserve_both_then_fall_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            store.load()
            path.write_text("corrupt-primary", encoding="utf-8")
            store.backup_path.write_text("corrupt-backup", encoding="utf-8")

            recovered = store.load()

            self.assertEqual(recovered["profile"]["name"], "Hydration hero")
            self.assertEqual(
                store.last_recovery_path.read_text(encoding="utf-8"),
                "corrupt-primary",
            )
            self.assertEqual(
                store.last_backup_recovery_path.read_text(encoding="utf-8"),
                "corrupt-backup",
            )
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                json.loads(store.backup_path.read_text(encoding="utf-8")),
            )

    def test_missing_primary_recovers_backup_and_missing_backup_is_seeded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            store = JsonStore(path)
            data = store.load()
            data["profile"]["name"] = "Backup resident"
            store.save(data)

            path.unlink()
            recovered = store.load()
            self.assertEqual(recovered["profile"]["name"], "Backup resident")
            self.assertTrue(path.is_file())

            store.backup_path.unlink()
            loaded = store.load()
            self.assertEqual(loaded["profile"]["name"], "Backup resident")
            self.assertTrue(store.backup_path.is_file())

    def test_directory_in_place_of_profile_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "water_buddy.json"
            path.mkdir()

            with self.assertRaises(StorageError):
                JsonStore(path).load()


if __name__ == "__main__":
    unittest.main()
