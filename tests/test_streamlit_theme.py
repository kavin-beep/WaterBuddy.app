"""Tests for synchronizing Water Buddy and Streamlit display modes."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from water_buddy import streamlit_theme


class StreamlitThemeSyncTests(unittest.TestCase):
    def test_four_themes_map_to_the_expected_streamlit_modes(self) -> None:
        expected = {
            "Dark": "dark",
            "Cyber": "dark",
            "Light": "light",
            "Japanese": "light",
        }
        for theme, mode in expected.items():
            with self.subTest(theme=theme):
                self.assertEqual(streamlit_theme.streamlit_mode_for(theme), mode)

    def test_unknown_theme_uses_the_safe_dark_default(self) -> None:
        self.assertEqual(streamlit_theme.streamlit_mode_for("unknown"), "dark")

    def test_mount_passes_desired_and_current_modes_to_the_component(self) -> None:
        with (
            patch.object(streamlit_theme, "_ensure_runtime_registration"),
            patch.object(
                streamlit_theme,
                "_current_streamlit_mode",
                return_value="light",
            ),
            patch.object(streamlit_theme, "_STREAMLIT_THEME_COMPONENT") as component,
        ):
            streamlit_theme.mount_streamlit_theme("Cyber")

        component.assert_called_once_with(
            key="water-buddy-streamlit-theme",
            data={"mode": "dark", "currentMode": "light"},
            height=0,
        )

    def test_javascript_uses_streamlits_own_theme_controls_and_cleans_up(self) -> None:
        source = streamlit_theme._STREAMLIT_THEME_JS
        self.assertIn('stMainMenuItem-theme-${', source)
        self.assertIn('stMainMenuButton', source)
        self.assertIn("root.style.colorScheme = desiredMode", source)
        self.assertIn("return cleanup", source)
        self.assertNotIn("localStorage", source)
        self.assertNotIn("postMessage", source)


if __name__ == "__main__":
    unittest.main()
