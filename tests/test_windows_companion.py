"""Pure integration contracts for the optional native companion."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from water_buddy.domain import WaterLogCooldownError, default_state, normalize_desktop_pet_settings
from water_buddy.mascot_design import MASCOT_ACCESSORIES, MASCOT_PALETTE
from water_buddy.storage import JsonStore
from windows_companion.ipc import COMMANDS, send_command
from windows_companion.launcher import ROUTES, route_url
from windows_companion.models import DesktopPetSettings, MascotState, next_state
from windows_companion.positioning import bottom_right, clamp_position
from windows_companion.profile_bridge import LocalJsonProfileBridge
from windows_companion.reminder_service import should_notify


class CompanionSettingsTests(unittest.TestCase):
    def test_disabled_by_default(self) -> None:
        self.assertFalse(default_state()["preferences"]["desktop_pet"]["enabled"])

    def test_malformed_settings_are_normalized(self) -> None:
        safe = normalize_desktop_pet_settings({"enabled": "no", "scale": 99, "position": {"x": "bad"}})
        self.assertFalse(safe["enabled"]); self.assertEqual(safe["scale"], 1.5); self.assertIsNone(safe["position"])

    def test_model_round_trip(self) -> None:
        model = DesktopPetSettings.from_mapping({"enabled": True, "position": {"x": 2, "y": 3}})
        self.assertTrue(model.enabled); self.assertEqual(model.position, (2, 3)); self.assertEqual(DesktopPetSettings.from_mapping(model.to_mapping()), model)

    def test_position_clamps_every_edge(self) -> None:
        self.assertEqual(clamp_position(-50, 900, 100, 100, (0, 0, 800, 600)), (0, 500))
        self.assertEqual(bottom_right(100, 100, (0, 0, 800, 600)), (676, 476))

    def test_native_and_in_app_mascots_share_visual_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        app_renderer = (root / "water_buddy" / "ui.py").read_text(encoding="utf-8")
        native_renderer = (root / "windows_companion" / "companion_app.py").read_text(encoding="utf-8")
        self.assertIn("from water_buddy.mascot_design import MASCOT_PALETTE", app_renderer)
        self.assertIn("from water_buddy.mascot_design import MASCOT_ACCESSORIES, MASCOT_PALETTE", native_renderer)
        self.assertEqual(MASCOT_PALETTE["body_mid"], "#20B6EB")
        for accessory in MASCOT_ACCESSORIES:
            with self.subTest(accessory=accessory): self.assertIn(accessory, native_renderer)


class CompanionStateTests(unittest.TestCase):
    def test_state_machine_events(self) -> None:
        expected = {"disable": MascotState.HIDDEN, "enable": MascotState.ENTRANCE, "water_logged": MascotState.HAPPY, "goal_reached": MascotState.CELEBRATE, "reminder_due": MascotState.THIRST_REMINDER, "clicked": MascotState.TALK, "double_clicked": MascotState.WAVE, "quiet_hours": MascotState.SLEEP}
        for event, state in expected.items():
            with self.subTest(event=event): self.assertEqual(next_state(MascotState.IDLE, event), state)

    def test_animation_returns_to_idle_but_hidden_stays_hidden(self) -> None:
        self.assertEqual(next_state(MascotState.HAPPY, "animation_complete"), MascotState.IDLE)
        self.assertEqual(next_state(MascotState.HIDDEN, "animation_complete"), MascotState.HIDDEN)

    def test_only_allowlisted_routes_and_commands(self) -> None:
        self.assertEqual(set(ROUTES), {"home", "reminders", "pet"})
        self.assertTrue(route_url("home").endswith("/home"))
        with self.assertRaises(ValueError): route_url("desktop")
        self.assertIn("SHUTDOWN", COMMANDS)
        with self.assertRaises(ValueError): send_command("DELETE_PROFILE")


class CompanionBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "profile.json"
        data = default_state(datetime(2026, 9, 6, 9, 0)); data["preferences"]["desktop_pet"]["enabled"] = True
        JsonStore(self.path).save(data); self.bridge = LocalJsonProfileBridge(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_quick_log_uses_shared_domain_and_pet_rewards(self) -> None:
        before = self.bridge.snapshot()["pet"]["xp"]
        result = self.bridge.log_water(250); after = self.bridge.snapshot()
        self.assertEqual(result["intake_ml"], 250); self.assertGreater(after["pet"]["xp"], before)
        entries = [entry for record in after["data"]["daily_records"].values() for entry in record["entries"]]
        self.assertEqual(entries[-1]["source"], "desktop mascot")

    def test_quick_log_keeps_sip_guard(self) -> None:
        self.bridge.log_water(250)
        with self.assertRaises(WaterLogCooldownError): self.bridge.log_water(250)

    def test_settings_update_same_profile(self) -> None:
        self.bridge.update_desktop_settings(always_on_top=False, position={"x": 9, "y": 12})
        settings = self.bridge.snapshot()["data"]["preferences"]["desktop_pet"]
        self.assertFalse(settings["always_on_top"]); self.assertEqual(settings["position"], {"x": 9, "y": 12})

    def test_recent_log_suppresses_due_reminder(self) -> None:
        now = datetime.now().replace(microsecond=0); data = self.bridge.snapshot()["data"]
        data["profile"]["wake_time"] = "00:00"; data["profile"]["sleep_time"] = "23:59"; data["preferences"]["quiet_start"] = "23:59"; data["preferences"]["quiet_end"] = "00:00"; data["preferences"]["next_reminder_at"] = (now - timedelta(minutes=1)).isoformat()
        today = data["daily_records"].setdefault(now.date().isoformat(), {"goal_ml": 2200, "intake_ml": 1, "entries": [], "completed_at": None, "reset_count": 0})
        today["entries"] = [{"id": "recent", "amount_ml": 1, "source": "test", "logged_at": now.isoformat()}]
        self.assertFalse(should_notify(data, now))
        today["entries"][0]["logged_at"] = (now - timedelta(minutes=11)).isoformat()
        self.assertTrue(should_notify(data, now))


class ProfilePlacementTests(unittest.TestCase):
    def test_desktop_pet_exists_only_in_profile_not_navigation(self) -> None:
        root = Path(__file__).resolve().parents[1]
        profile = (root / "app_pages" / "profile.py").read_text(encoding="utf-8")
        shell = (root / "streamlit_app.py").read_text(encoding="utf-8")
        self.assertIn('st.subheader("Desktop Pet")', profile)
        self.assertIn('"Enable desktop mascot"', profile)
        self.assertNotIn("app_pages/desktop_pet.py", shell)
        self.assertFalse((root / "app_pages" / "desktop_pet.py").exists())


if __name__ == "__main__":
    unittest.main()
