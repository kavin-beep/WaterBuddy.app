"""Focused page coverage for Pet quest volume display preferences."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

from water_buddy.domain import default_state
from water_buddy.storage import JsonStore

ROOT = Path(__file__).resolve().parents[1]


class PetQuestUnitTests(unittest.TestCase):
    def test_hydration_quest_uses_selected_ounce_display(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            data = default_state()
            data["preferences"]["units"] = "oz"
            record = next(iter(data["daily_records"].values()))
            record["intake_ml"] = 250

            app = AppTest.from_file(
                ROOT / "app_pages" / "pet.py",
                default_timeout=20,
            )
            app.session_state["data"] = data
            app.session_state["store"] = JsonStore(
                Path(temporary_directory) / "pet-units.json"
            )
            app.session_state["flash_message"] = None
            app.run()

            self.assertEqual(list(app.exception), [])
            progress_labels = {
                str(element.text) for element in app.get("progress")
            }
            self.assertIn("8.5 fl oz of 74.4 fl oz", progress_labels)
            self.assertNotIn("250 of 2200 ml", progress_labels)


if __name__ == "__main__":
    unittest.main()
