"""Validation, persistence, isolation, and UI checks for FLOW settings actions."""
from copy import deepcopy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest
from water_buddy.coach_settings import (
    SettingsProposal, apply_settings, settings_snapshot, validate_changes,
)
from water_buddy.domain import default_state, progress_summary
from water_buddy.groq_coach import GroqError, groq_reply
from water_buddy.storage import JsonStore, StorageError

ROOT = Path(__file__).resolve().parents[1]


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = JsonStore(Path(self.directory.name) / "user.json")
        self.data = default_state()
        self.store.save(self.data)

    def test_validation_rejects_unknown_and_invalid_fields(self):
        cases = [{}, {"api_key": "x"}, {"user_id": "another"}, {"theme": "Pink"},
                 {"units": "litres"}, {"reminders_enabled": "false"},
                 {"daily_goal_ml": True}, {"daily_goal_ml": 2500.5},
                 {"daily_goal_ml": 499}, {"daily_goal_ml": 8001},
                 {"reminder_interval_minutes": 20}, {"quiet_start": "25:00"},
                 {"display_name": " "}, {"pet_name": "x" * 25},
                 {"display_name": "Name\nInstruction"}, {"sound_enabled": 0}]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_changes(change)

    def test_multi_setting_save_and_reload_preserves_other_account(self):
        other = JsonStore(Path(self.directory.name) / "other.json")
        other.save(default_state())
        other_before = other.path.read_bytes()
        original_logs = deepcopy(self.data["daily_records"])
        summary = apply_settings(self.data, self.store, {
            "theme": "Cyber", "units": "oz", "sound_enabled": False,
            "display_name": "Tester", "pet_name": "Splash",
            "reminders_enabled": False, "quiet_start": "21:30",
        }, settings_snapshot(self.data))
        saved = self.store.load()
        self.assertEqual(saved["preferences"]["theme"], "Cyber")
        self.assertEqual(saved["profile"]["pet"]["name"], "Splash")
        self.assertEqual(saved["profile"]["mascot_name"], "Splash")
        self.assertIsNone(saved["preferences"]["next_reminder_at"])
        self.assertEqual(saved["daily_records"], original_logs)
        self.assertEqual(other.path.read_bytes(), other_before)
        self.assertTrue(summary.startswith("Saved:"))

    def test_goal_updates_current_record_and_automatic_mode(self):
        apply_settings(self.data, self.store, {"daily_goal_ml": 2500}, settings_snapshot(self.data))
        self.assertEqual(progress_summary(self.data)["goal_ml"], 2500)
        self.assertEqual(self.store.load()["profile"]["manual_goal_ml"], 2500)
        apply_settings(self.data, self.store, {"daily_goal_ml": None}, settings_snapshot(self.data))
        self.assertIsNone(self.data["profile"]["manual_goal_ml"])
        self.assertEqual(progress_summary(self.data)["goal_ml"], 2200)

    def test_invalid_batch_and_save_failure_leave_session_unchanged(self):
        before = deepcopy(self.data)
        with self.assertRaises(ValueError):
            apply_settings(self.data, self.store, {"theme": "Light", "daily_goal_ml": -2}, settings_snapshot(self.data))
        self.assertEqual(self.data, before)
        with patch.object(self.store, "save", side_effect=StorageError("Unavailable")):
            with self.assertRaises(StorageError):
                apply_settings(self.data, self.store, {"theme": "Light"}, settings_snapshot(self.data))
        self.assertEqual(self.data, before)

    def test_stale_preview_rejected_but_unrelated_saved_changes_retained(self):
        expected = settings_snapshot(self.data)
        latest = self.store.load()
        latest["preferences"]["theme"] = "Japanese"
        latest["profile"]["name"] = "Updated elsewhere"
        self.store.save(latest)
        with self.assertRaises(ValueError):
            apply_settings(self.data, self.store, {"theme": "Light"}, expected)
        apply_settings(self.data, self.store, {"units": "oz"}, expected)
        self.assertEqual(self.data["profile"]["name"], "Updated elsewhere")
        self.assertEqual(self.data["preferences"]["theme"], "Japanese")

    def test_reminder_change_schedules_new_interval(self):
        moment = datetime(2026, 10, 29, 12)
        with patch("water_buddy.coach_settings.local_now", return_value=moment):
            apply_settings(self.data, self.store, {"reminder_interval_minutes": 30}, settings_snapshot(self.data))
        self.assertEqual(self.data["preferences"]["next_reminder_at"], "2026-10-29T12:30:00")

    def mock_response(self, function="prepare_settings_update", arguments='{"theme":"Light"}'):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"choices": [{"message": {
            "content": None, "tool_calls": [{"function": {"name": function, "arguments": arguments}}],
        }}]})
        return response

    def test_tool_call_becomes_validated_proposal_without_writes(self):
        before = self.store.path.read_bytes()
        with patch("water_buddy.groq_coach.urlopen", return_value=self.mock_response()):
            reply = groq_reply("fake", [{"role": "assistant", "content": "intro"}, {"role": "user", "content": "Switch to Light"}], {})
        self.assertIsInstance(reply, SettingsProposal)
        self.assertEqual(reply.changes, {"theme": "Light"})
        self.assertEqual(before, self.store.path.read_bytes())

    def test_bad_tool_calls_are_not_executed(self):
        for function, arguments in [("delete_account", "{}"), ("prepare_settings_update", '{"theme":"invalid"}'), ("prepare_settings_update", "not json")]:
            with self.subTest(function=function, arguments=arguments), patch("water_buddy.groq_coach.urlopen", return_value=self.mock_response(function, arguments)):
                with self.assertRaises(GroqError):
                    groq_reply("fake", [], {})

    def app(self):
        app = AppTest.from_file(str(ROOT / "app_pages/coach.py"), default_timeout=20)
        app.session_state["data"] = deepcopy(self.data)
        app.session_state["store"] = self.store
        app.session_state["active_user_id"] = "test-user"
        return app

    def test_preview_apply_persists_once_and_refreshes_ui_state(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake"}), patch("water_buddy.groq_coach.groq_reply", return_value=SettingsProposal({"theme": "Light", "daily_goal_ml": 2500})) as reply:
            app = self.app().run()
            app.chat_input[0].set_value("Use Light theme and a 2500 ml goal").run()
            self.assertFalse(app.exception)
            self.assertEqual(self.store.load()["preferences"]["theme"], "Dark")
            self.assertEqual(len(app.table), 1)
            app.session_state["profile_theme"] = "Dark"
            app.button(key="coach_apply_settings").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(self.store.load()["preferences"]["theme"], "Light")
            self.assertEqual(progress_summary(app.session_state["data"])["goal_ml"], 2500)
            self.assertNotIn("profile_theme", app.session_state)
            self.assertNotIn("coach_pending_settings", app.session_state)
            self.assertIn("Saved:", app.session_state["coach_messages"][-1]["content"])
            app.run()
            self.assertEqual(reply.call_count, 1)

    def test_cancel_and_clear_discard_preview(self):
        for button in ("coach_cancel_settings", "coach_clear_chat"):
            with self.subTest(button=button), patch.dict(os.environ, {"GROQ_API_KEY": "fake"}), patch("water_buddy.groq_coach.groq_reply", return_value=SettingsProposal({"theme": "Light"})):
                app = self.app().run()
                app.chat_input[0].set_value("Light theme please").run()
                app.button(key=button).click().run()
                self.assertFalse(app.exception)
                self.assertNotIn("coach_pending_settings", app.session_state)
                self.assertEqual(self.store.load()["preferences"]["theme"], "Dark")

    def test_cross_account_preview_is_removed(self):
        app = self.app()
        app.session_state["coach_pending_settings"] = {
            "changes": {"theme": "Light"}, "expected": settings_snapshot(self.data), "owner": "another-user",
        }
        app.run()
        self.assertFalse(app.exception)
        self.assertNotIn("coach_pending_settings", app.session_state)

    def test_ui_save_failure_never_claims_success(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": "fake"}), patch("water_buddy.groq_coach.groq_reply", return_value=SettingsProposal({"theme": "Light"})):
            app = self.app().run()
            app.chat_input[0].set_value("Light theme please").run()
            with patch.object(self.store, "save", side_effect=StorageError("Failed")):
                app.button(key="coach_apply_settings").click().run()
            self.assertFalse(app.exception)
            self.assertIn("couldn't confirm", app.session_state["coach_messages"][-1]["content"])
            self.assertEqual(app.session_state["data"]["preferences"]["theme"], "Dark")


if __name__ == "__main__":
    unittest.main()
