"""Regression coverage for Streamlit shell and page-state hardening."""

from __future__ import annotations

import ast
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from water_buddy.auth import AccountStore
from water_buddy.domain import default_state
from water_buddy.storage import JsonStore

ROOT = Path(__file__).resolve().parents[1]


def _ast_for(relative_path: str) -> ast.Module:
    return ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))


def _page_app(
    page_name: str,
    data: dict,
    directory: str,
) -> AppTest:
    app = AppTest.from_file(
        ROOT / "app_pages" / page_name,
        default_timeout=30,
    )
    app.session_state["data"] = data
    app.session_state["store"] = JsonStore(Path(directory) / f"{page_name}.json")
    app.session_state["flash_message"] = None
    app.session_state["sound_event"] = None
    app.session_state["celebrate_once"] = False
    return app.run()


class ShellHardeningTests(unittest.TestCase):
    def test_dialog_dismiss_callback_reschedules_and_persists(self) -> None:
        module = _ast_for("streamlit_app.py")
        callback = next(
            node
            for node in module.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_close_reminder_dialog"
        )
        called_names = {
            node.func.id
            for node in ast.walk(callback)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }

        self.assertIn("dismiss_reminder", called_names)
        self.assertIn("_save_with_flash", called_names)

    def test_invalid_auth_clears_user_state_but_preserves_login_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            account_store = AccountStore(
                Path(directory) / "accounts.json",
                pbkdf2_iterations=100_000,
            )
            app = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=30)
            app.session_state["account_store"] = account_store
            app.session_state["auth_user"] = {"user_id": "not-a-valid-uuid"}
            user_scoped_values = {
                "account_init_error": "stale profile error",
                "coach_messages": [{"role": "user", "content": "private"}],
                "custom_log_amount": 750,
                "insights_window": 30,
                "pending_water_buddy_restore": {"profile": {"name": "Other"}},
                "pet_accessory_choice": "crown",
                "profile_name": "Previous user",
                "reminders_test_active": True,
                "today_entries_table": {"selection": {"rows": [0]}},
            }
            for key, value in user_scoped_values.items():
                app.session_state[key] = value
            app.session_state["login_mode"] = "Create account"
            app.session_state["login_create_password"] = "unfinished-passphrase"
            app.session_state["unrelated_session_value"] = "keep"

            with patch.dict(
                "os.environ",
                {"WATER_BUDDY_DATA_DIR": directory},
            ):
                app.run()

            self.assertEqual(list(app.exception), [])
            for key in user_scoped_values:
                self.assertNotIn(key, app.session_state)
            self.assertIs(app.session_state["account_store"], account_store)
            self.assertEqual(app.session_state["login_mode"], "Create account")
            self.assertEqual(
                app.session_state["login_create_password"],
                "unfinished-passphrase",
            )
            self.assertEqual(app.session_state["unrelated_session_value"], "keep")


class InsightsHardeningTests(unittest.TestCase):
    def test_new_account_with_no_activity_renders_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            app = _page_app("insights.py", default_state(), directory)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(list(app.metric), [])
        self.assertTrue(
            any(
                "Your trends will appear here" in str(element.proto.body)
                for element in app.get("html")
            )
        )

    def test_history_window_starts_on_account_creation_day(self) -> None:
        now = datetime.now(timezone.utc).astimezone()
        data = default_state(now)
        today_key = now.date().isoformat()
        data["metadata"]["created_at"] = (now - timedelta(days=1)).isoformat(
            timespec="seconds"
        )
        data["daily_records"][today_key]["intake_ml"] = 500

        with tempfile.TemporaryDirectory() as directory:
            app = _page_app("insights.py", data, directory)

        self.assertEqual(list(app.exception), [])
        metrics = {metric.label: metric for metric in app.metric}
        self.assertEqual(metrics["Goals reached"].value, "0 of 2")


class AchievementHardeningTests(unittest.TestCase):
    def test_exhausted_milestone_sets_render_completed_states(self) -> None:
        now = datetime.now(timezone.utc).astimezone()
        data = default_state(now)
        records: dict[str, dict[str, object]] = {}
        for offset in range(101):
            day = now.date() - timedelta(days=offset)
            records[day.isoformat()] = {
                "goal_ml": 2200,
                "intake_ml": 2200,
                "entries": [],
                "completed_at": now.isoformat(timespec="seconds"),
                "reset_count": 0,
            }
        data["daily_records"] = records

        with tempfile.TemporaryDirectory() as directory:
            app = _page_app("achievements.py", data, directory)

        self.assertEqual(list(app.exception), [])
        rendered_markdown = [str(element.value) for element in app.markdown]
        self.assertTrue(
            any(
                "Every listed streak milestone is complete" in value
                for value in rendered_markdown
            )
        )
        self.assertTrue(
            any(
                "Every listed goal-day milestone is complete" in value
                for value in rendered_markdown
            )
        )
        self.assertTrue(
            any(
                "Every listed journey-volume milestone is complete" in value
                for value in rendered_markdown
            )
        )


class LoginHardeningTests(unittest.TestCase):
    def test_login_forms_preserve_values_after_failed_submission(self) -> None:
        module = _ast_for("app_pages/login.py")
        forms: dict[str, bool] = {}
        for node in ast.walk(module):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "form"
                and node.args
            ):
                continue
            form_name = ast.literal_eval(node.args[0])
            clear_on_submit = next(
                ast.literal_eval(keyword.value)
                for keyword in node.keywords
                if keyword.arg == "clear_on_submit"
            )
            forms[form_name] = clear_on_submit

        self.assertEqual(
            forms,
            {
                "create_account_form": False,
                "sign_in_form": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
