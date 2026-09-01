"""Streamlit smoke tests for every Water Buddy page."""

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from streamlit.testing.v1 import AppTest

from water_buddy.auth import AccountStore
from water_buddy.domain import default_state
from water_buddy.pet import LEVEL_XP_THRESHOLDS, pet_snapshot
from water_buddy.storage import JsonStore

ROOT = Path(__file__).resolve().parents[1]
PAGE_FILES = (
    "home.py",
    "log_water.py",
    "insights.py",
    "achievements.py",
    "reminders.py",
    "coach.py",
    "pet.py",
    "profile.py",
)
PAGE_AMBIENCE_VARIANTS = {
    "login.py": "welcome",
    "home.py": "home",
    "log_water.py": "log",
    "pet.py": "pet",
    "insights.py": "insights",
    "achievements.py": "achievements",
    "reminders.py": "reminders",
    "coach.py": "coach",
    "profile.py": "profile",
}


class PageSmokeTests(unittest.TestCase):
    def test_navigation_contract_uses_responsive_discoverable_sidebar(self) -> None:
        module = ast.parse((ROOT / "streamlit_app.py").read_text(encoding="utf-8"))

        page_config = next(
            node
            for node in ast.walk(module)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "set_page_config"
        )
        page_config_keywords = {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in page_config.keywords
            if keyword.arg is not None
        }
        self.assertEqual(page_config_keywords["initial_sidebar_state"], "auto")

        assignments = {
            target.id: node.value
            for node in ast.walk(module)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        navigation = assignments["navigation"]
        self.assertIsInstance(navigation, ast.Call)
        navigation_keywords = {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in navigation.keywords
            if keyword.arg is not None
        }
        self.assertEqual(navigation_keywords["position"], "sidebar")
        self.assertTrue(navigation_keywords["expanded"])

        login_navigation = assignments["login_navigation"]
        self.assertIsInstance(login_navigation, ast.Call)
        login_keywords = {
            keyword.arg: ast.literal_eval(keyword.value)
            for keyword in login_navigation.keywords
            if keyword.arg is not None
        }
        self.assertEqual(login_keywords["position"], "hidden")

        pages = assignments["pages"]
        self.assertIsInstance(pages, ast.Dict)
        self.assertEqual(
            [ast.literal_eval(key) for key in pages.keys],
            ["", "Progress", "Your plan"],
        )
        page_contracts: dict[str, tuple[str, str]] = {}
        for group in pages.values:
            self.assertIsInstance(group, ast.List)
            for page in group.elts:
                self.assertIsInstance(page, ast.Call)
                keywords = {
                    keyword.arg: ast.literal_eval(keyword.value)
                    for keyword in page.keywords
                    if keyword.arg in {"title", "icon", "url_path"}
                }
                page_contracts[keywords["title"]] = (
                    keywords["icon"],
                    keywords["url_path"],
                )
        self.assertEqual(
            page_contracts,
            {
                "Home": (":material/home:", "home"),
                "Log water": (":material/water_drop:", "log"),
                "Pet room": (":material/pets:", "pet"),
                "Insights": (":material/monitoring:", "insights"),
                "Achievements": (":material/workspace_premium:", "achievements"),
                "Reminders": (":material/notifications:", "reminders"),
                "FLOW coach": (":material/chat_bubble:", "coach"),
                "Profile": (":material/tune:", "profile"),
            },
        )

    def test_every_page_declares_one_expected_ambience(self) -> None:
        for page_name, expected_variant in PAGE_AMBIENCE_VARIANTS.items():
            with self.subTest(page=page_name):
                module = ast.parse(
                    (ROOT / "app_pages" / page_name).read_text(encoding="utf-8")
                )
                ui_imports = {
                    alias.name
                    for node in module.body
                    if isinstance(node, ast.ImportFrom)
                    and node.module == "water_buddy.ui"
                    for alias in node.names
                }
                self.assertIn("mount_page_ambience", ui_imports)

                ambience_calls = [
                    node
                    for node in ast.walk(module)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "mount_page_ambience"
                ]
                self.assertEqual(len(ambience_calls), 1)
                call = ambience_calls[0]
                self.assertEqual(len(call.args), 1)
                self.assertEqual(ast.literal_eval(call.args[0]), expected_variant)

    def test_every_page_renders_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            for page_name in PAGE_FILES:
                with self.subTest(page=page_name):
                    store = JsonStore(Path(temporary_directory) / f"{page_name}.json")
                    app = AppTest.from_file(
                        ROOT / "app_pages" / page_name,
                        default_timeout=20,
                    )
                    app.session_state["data"] = default_state()
                    app.session_state["store"] = store
                    app.session_state["flash_message"] = None
                    app.session_state["sound_event"] = None
                    app.session_state["celebrate_once"] = False
                    app.run()
                    self.assertEqual(
                        list(app.exception),
                        [],
                        msg=f"{page_name} raised a Streamlit exception",
                    )

    def test_login_page_renders_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            app = AppTest.from_file(
                ROOT / "app_pages" / "login.py",
                default_timeout=20,
            )
            app.session_state["account_store"] = AccountStore(
                Path(temporary_directory) / "accounts.json",
                pbkdf2_iterations=100_000,
            )
            app.run()
            self.assertEqual(list(app.exception), [])

    def test_logged_out_shell_shows_welcome_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.dict(
                "os.environ",
                {"WATER_BUDDY_DATA_DIR": temporary_directory},
            ):
                app = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=20)
                app.run()
            self.assertEqual(list(app.exception), [])

    def test_create_account_form_starts_a_public_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            app = AppTest.from_file(
                ROOT / "app_pages" / "login.py",
                default_timeout=20,
            )
            app.session_state["account_store"] = AccountStore(
                Path(temporary_directory) / "accounts.json",
                pbkdf2_iterations=100_000,
            )
            app.run()
            app.segmented_control[0].set_value("Create account").run()

            fields = {field.label: field for field in app.text_input}
            fields["Your name"].set_value("Ava Test")
            fields["Email address"].set_value("ava@example.com")
            fields["Password"].set_value("a-local-passphrase")
            fields["Confirm password"].set_value("a-local-passphrase")
            app.checkbox[0].check()
            app.button[0].click().run()

            self.assertEqual(list(app.exception), [])
            self.assertEqual(
                app.session_state["auth_user"]["email"],
                "ava@example.com",
            )
            self.assertNotIn(
                "a-local-passphrase",
                [field.value for field in app.text_input],
            )

    def test_authenticated_shell_mounts_user_file_and_signs_out(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            account = AccountStore(
                Path(temporary_directory) / "accounts.json",
                pbkdf2_iterations=100_000,
            ).register("Ava Test", "ava@example.com", "a-local-passphrase")

            with patch.dict(
                "os.environ",
                {"WATER_BUDDY_DATA_DIR": temporary_directory},
            ):
                app = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=30)
                app.session_state["auth_user"] = account
                app.run()
                self.assertEqual(list(app.exception), [])
                self.assertEqual(
                    app.session_state["data"]["profile"]["name"],
                    "Ava Test",
                )
                user_file = Path(app.session_state["store"].path)
                self.assertEqual(user_file.parent.name, "users")
                self.assertTrue(user_file.is_file())

                sign_out = next(
                    button for button in app.button if button.label == "Sign out"
                )
                sign_out.click().run()

            self.assertEqual(list(app.exception), [])
            self.assertNotIn("auth_user", app.session_state)
            self.assertIn("Welcome to Water Buddy", [item.value for item in app.subheader])

    def test_profile_storage_error_still_allows_sign_out(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            account = AccountStore(
                Path(temporary_directory) / "accounts.json",
                pbkdf2_iterations=100_000,
            ).register("Ava Test", "ava@example.com", "a-local-passphrase")
            safe_user_id = UUID(str(account["user_id"])).hex
            broken_profile_path = (
                Path(temporary_directory) / "users" / f"{safe_user_id}.json"
            )
            broken_profile_path.mkdir(parents=True)

            with patch.dict(
                "os.environ",
                {"WATER_BUDDY_DATA_DIR": temporary_directory},
            ):
                app = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=30)
                app.session_state["auth_user"] = account
                app.run()
                self.assertEqual(list(app.exception), [])
                self.assertTrue(
                    any(
                        "could not safely open" in error.value
                        for error in app.error
                    )
                )
                next(
                    button for button in app.button if button.label == "Sign out"
                ).click().run()

            self.assertEqual(list(app.exception), [])
            self.assertNotIn("auth_user", app.session_state)

    def test_sign_in_form_authenticates_existing_account(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = AccountStore(
                Path(temporary_directory) / "accounts.json",
                pbkdf2_iterations=100_000,
            )
            store.register("Returning User", "return@example.com", "safe-pass-123")
            app = AppTest.from_file(
                ROOT / "app_pages" / "login.py",
                default_timeout=20,
            )
            app.session_state["account_store"] = store
            app.run()

            fields = {field.label: field for field in app.text_input}
            fields["Email address"].set_value("return@example.com")
            fields["Password"].set_value("safe-pass-123")
            app.button[0].click().run()

            self.assertEqual(list(app.exception), [])
            self.assertEqual(
                app.session_state["auth_user"]["display_name"],
                "Returning User",
            )
            self.assertNotIn(
                "safe-pass-123",
                [field.value for field in app.text_input],
            )

    def test_pet_room_care_action_persists_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "pet-room.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "pet.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.run()

            starting_xp = pet_snapshot(app.session_state["data"])["xp"]
            play = next(
                button for button in app.button if button.label == "Play together"
            )
            play.click().run()

            self.assertEqual(list(app.exception), [])
            self.assertGreater(
                pet_snapshot(app.session_state["data"])["xp"],
                starting_xp,
            )
            self.assertEqual(
                pet_snapshot(store.load())["xp"],
                pet_snapshot(app.session_state["data"])["xp"],
            )

    def test_level_outfit_roadmap_unlocks_and_equips_cool_guy_fit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "outfit-room.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "pet.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.run()

            locked_labels = {button.label for button in app.button if button.disabled}
            self.assertIn("Unlocks at level 10", locked_labels)
            self.assertIn("Unlocks at level 15", locked_labels)
            self.assertIn("Unlocks at level 20", locked_labels)

            app.session_state["data"]["profile"]["pet"]["xp"] = (
                LEVEL_XP_THRESHOLDS[-1]
            )
            app.run()
            cool_guy_button = next(
                button
                for button in app.button
                if button.key == "pet_outfit_cool_guy_fit"
            )
            cool_guy_button.click().run()

            self.assertEqual(list(app.exception), [])
            self.assertEqual(
                pet_snapshot(app.session_state["data"])["equipped_accessory"],
                "cool_guy_fit",
            )
            self.assertEqual(
                pet_snapshot(store.load())["equipped_accessory"],
                "cool_guy_fit",
            )

    def test_experience_controls_apply_and_persist_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "experience.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "profile.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.run()

            next(
                control
                for control in app.segmented_control
                if control.label == "App theme"
            ).set_value("Light").run()
            next(
                control
                for control in app.toggle
                if control.label == "Motion effects"
            ).set_value(False).run()
            next(
                control
                for control in app.segmented_control
                if control.label == "Click volume"
            ).set_value("Vivid").run()
            next(
                control
                for control in app.segmented_control
                if control.label == "Volume display"
            ).set_value("oz").run()
            next(
                control
                for control in app.toggle
                if control.label == "Interface sounds"
            ).set_value(False).run()

            self.assertEqual(list(app.exception), [])
            number_input_labels = {control.label for control in app.number_input}
            self.assertIn("Custom occupation adjustment (fl oz)", number_input_labels)
            self.assertIn("Daily goal (fl oz)", number_input_labels)
            self.assertIn("+8.5 fl oz", {button.label for button in app.button})

            next(
                control
                for control in app.toggle
                if control.label == "Set my own daily goal"
            ).set_value(True).run()
            next(
                control
                for control in app.number_input
                if control.label == "Daily goal (fl oz)"
            ).set_value(80.0)
            next(
                button for button in app.button if button.label == "Save profile & plan"
            ).click().run()

            self.assertEqual(list(app.exception), [])
            preferences = app.session_state["data"]["preferences"]
            self.assertEqual(preferences["theme"], "Light")
            self.assertFalse(preferences["background_motion"])
            self.assertEqual(preferences["interface_sound_volume"], "Vivid")
            self.assertEqual(preferences["units"], "oz")
            self.assertFalse(preferences["sound_enabled"])
            self.assertEqual(
                app.session_state["data"]["profile"]["manual_goal_ml"],
                2366,
            )
            self.assertEqual(store.load()["preferences"], preferences)

    def test_imperial_logging_uses_consistent_labels_and_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "imperial-log.json")
            data = default_state()
            data["preferences"]["units"] = "oz"
            app = AppTest.from_file(
                ROOT / "app_pages" / "log_water.py",
                default_timeout=20,
            )
            app.session_state["data"] = data
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.session_state["sound_event"] = None
            app.session_state["celebrate_once"] = False
            app.run()

            labels = {button.label for button in app.button}
            self.assertIn("+8.5 fl oz", labels)
            amount = next(
                field for field in app.number_input if field.label == "Amount (fl oz)"
            )
            amount.set_value(10.0)
            next(
                button for button in app.button if button.label == "Add to today"
            ).click().run()

            self.assertEqual(list(app.exception), [])
            today = next(iter(app.session_state["data"]["daily_records"].values()))
            self.assertEqual(today["intake_ml"], 296)

    def test_entry_editor_accepts_full_domain_range_in_imperial_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "imperial-editor-range.json")
            data = default_state()
            data["preferences"]["units"] = "oz"
            today = next(iter(data["daily_records"].values()))
            logged_at = (
                datetime.now(timezone.utc).astimezone().replace(tzinfo=None)
                - timedelta(minutes=1)
            ).isoformat(timespec="seconds")
            today["intake_ml"] = 5001
            today["entries"] = [
                {
                    "id": "small-entry",
                    "amount_ml": 1,
                    "source": "Water",
                    "logged_at": logged_at,
                },
                {
                    "id": "large-entry",
                    "amount_ml": 5000,
                    "source": "Bottle refill",
                    "logged_at": logged_at,
                },
            ]

            app = AppTest.from_file(
                ROOT / "app_pages" / "log_water.py",
                default_timeout=20,
            )
            app.session_state["data"] = data
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.session_state["sound_event"] = None
            app.session_state["celebrate_once"] = False
            app.run()

            self.assertEqual(list(app.exception), [])
            next(
                control
                for control in app.selectbox
                if control.label == "Choose an entry"
            ).set_value("large-entry").run()
            self.assertEqual(list(app.exception), [])

    def test_water_entry_can_be_corrected_then_deleted_with_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "entry-correction.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "log_water.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.session_state["sound_event"] = None
            app.session_state["celebrate_once"] = False
            app.run()

            next(button for button in app.button if button.label == "+250 ml").click().run()
            today = next(iter(app.session_state["data"]["daily_records"].values()))
            original_entry = today["entries"][0].copy()

            next(
                field
                for field in app.number_input
                if field.label == "Corrected amount (ml)"
            ).set_value(650)
            next(
                field
                for field in app.selectbox
                if field.label == "Corrected source"
            ).set_value("Meal")
            next(
                button for button in app.button if button.label == "Save correction"
            ).click().run()

            self.assertEqual(list(app.exception), [])
            corrected_today = next(
                iter(app.session_state["data"]["daily_records"].values())
            )
            self.assertEqual(corrected_today["intake_ml"], 650)
            self.assertEqual(len(corrected_today["entries"]), 1)
            corrected_entry = corrected_today["entries"][0]
            self.assertEqual(corrected_entry["id"], original_entry["id"])
            self.assertEqual(corrected_entry["logged_at"], original_entry["logged_at"])
            self.assertEqual(corrected_entry["amount_ml"], 650)
            self.assertEqual(corrected_entry["source"], "Meal")
            persisted_today = next(iter(store.load()["daily_records"].values()))
            self.assertEqual(persisted_today, corrected_today)

            next(
                button
                for button in app.button
                if button.label == "Delete selected entry"
            ).click().run()
            self.assertTrue(
                any(
                    "Remove 650 ml from today" in warning.value
                    for warning in app.warning
                )
            )
            # AppTest performs full-script reruns, while dialog buttons trigger a
            # fragment rerun in the browser. Re-trigger the opener alongside the
            # dialog action so both paths are represented in the full rerun.
            app.button("open_delete_selected_entry").click()
            app.button("keep_selected_water_entry").click().run()
            kept_today = next(
                iter(app.session_state["data"]["daily_records"].values())
            )
            self.assertEqual(kept_today["intake_ml"], 650)
            self.assertEqual(len(kept_today["entries"]), 1)

            next(
                button
                for button in app.button
                if button.label == "Delete selected entry"
            ).click().run()
            app.button("open_delete_selected_entry").click()
            app.button("delete_selected_water_entry").click().run()

            self.assertEqual(list(app.exception), [])
            deleted_today = next(
                iter(app.session_state["data"]["daily_records"].values())
            )
            self.assertEqual(deleted_today["intake_ml"], 0)
            self.assertEqual(deleted_today["entries"], [])
            persisted_deleted_today = next(iter(store.load()["daily_records"].values()))
            self.assertEqual(persisted_deleted_today, deleted_today)

    def test_restore_preview_requires_confirmation_and_cancel_preserves_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "restore-cancel.json")
            current = default_state()
            current["profile"]["name"] = "Current profile"
            store.save(current)

            candidate = default_state()
            candidate["profile"]["name"] = "Backup candidate"
            candidate_bytes = json.dumps(candidate).encode("utf-8")

            app = AppTest.from_file(
                ROOT / "app_pages" / "profile.py",
                default_timeout=20,
            )
            app.session_state["data"] = current
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.run()

            app.file_uploader("restore_backup_file").set_value(
                ("water-buddy-backup.json", candidate_bytes, "application/json")
            ).run()
            app.button("restore_backup_button").click().run()

            self.assertTrue(
                any(
                    "Restoring replaces this account" in warning.value
                    for warning in app.warning
                )
            )
            self.assertEqual(app.session_state["data"]["profile"]["name"], "Current profile")

            # AppTest performs full-script reruns; keep the dialog opener active
            # alongside its fragment action to model the browser interaction.
            app.button("restore_backup_button").click()
            app.button("cancel_restore_backup").click().run()

            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.session_state["data"]["profile"]["name"], "Current profile")
            self.assertEqual(store.load()["profile"]["name"], "Current profile")
            self.assertNotIn("pending_water_buddy_restore", app.session_state)

            app.button("restore_backup_button").click().run()
            self.assertEqual(app.session_state["data"]["profile"]["name"], "Current profile")
            app.button("restore_backup_button").click()
            app.button("confirm_restore_backup").click().run()

            self.assertEqual(list(app.exception), [])
            self.assertEqual(app.session_state["data"]["profile"]["name"], "Backup candidate")
            self.assertEqual(store.load()["profile"]["name"], "Backup candidate")
            self.assertNotIn("pending_water_buddy_restore", app.session_state)

    def test_home_sip_guard_blocks_a_repeat_quick_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "home-sip-guard.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "home.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.session_state["sound_event"] = None
            app.session_state["celebrate_once"] = False
            app.run()

            next(button for button in app.button if button.label == "+250 ml").click().run()
            saved_after_first = store.path.read_bytes()
            next(button for button in app.button if button.label == "+250 ml").click().run()

            summary = app.session_state["data"]["daily_records"]
            today = next(iter(summary.values()))
            self.assertEqual(today["intake_ml"], 250)
            self.assertEqual(len(today["entries"]), 1)
            self.assertEqual(store.path.read_bytes(), saved_after_first)
            self.assertIsNone(app.session_state["sound_event"])
            self.assertTrue(
                any("Sip Guard" in warning.value for warning in app.warning)
            )

    def test_stale_celebration_flag_does_not_celebrate_incomplete_day(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "stale-celebration.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "home.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.session_state["sound_event"] = None
            app.session_state["celebrate_once"] = True
            app.run()

            self.assertEqual(list(app.exception), [])
            self.assertFalse(
                any("Daily goal complete" in success.value for success in app.success)
            )
            self.assertNotIn("celebrate_once", app.session_state)

    def test_custom_water_sip_guard_blocks_a_repeat_submission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            store = JsonStore(Path(temporary_directory) / "custom-sip-guard.json")
            app = AppTest.from_file(
                ROOT / "app_pages" / "log_water.py",
                default_timeout=20,
            )
            app.session_state["data"] = default_state()
            app.session_state["store"] = store
            app.session_state["flash_message"] = None
            app.session_state["sound_event"] = None
            app.session_state["celebrate_once"] = False
            app.run()

            next(
                field for field in app.number_input if field.label == "Amount (ml)"
            ).set_value(300)
            next(
                button for button in app.button if button.label == "Add to today"
            ).click().run()
            saved_after_first = store.path.read_bytes()
            next(
                button for button in app.button if button.label == "Add to today"
            ).click().run()

            summary = app.session_state["data"]["daily_records"]
            today = next(iter(summary.values()))
            self.assertEqual(today["intake_ml"], 300)
            self.assertEqual(len(today["entries"]), 1)
            self.assertEqual(store.path.read_bytes(), saved_after_first)
            self.assertIsNone(app.session_state["sound_event"])
            self.assertTrue(
                any("Sip Guard" in warning.value for warning in app.warning)
            )


if __name__ == "__main__":
    unittest.main()
