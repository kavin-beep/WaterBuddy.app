"""Accessibility checks for Water Buddy's native Streamlit theme tokens."""

from __future__ import annotations

import unittest
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
THEME_PATH = ROOT / ".streamlit" / "config.toml"
AA_NORMAL_TEXT_CONTRAST = 4.5


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


class ThemeAccessibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = tomllib.loads(THEME_PATH.read_text(encoding="utf-8"))

    def test_primary_buttons_have_readable_white_text(self) -> None:
        theme = self.config["theme"]
        variants = {
            "light": theme["light"],
            "light sidebar": theme["light"]["sidebar"],
            "dark": theme["dark"],
            "dark sidebar": theme["dark"]["sidebar"],
        }

        for name, tokens in variants.items():
            with self.subTest(theme=name):
                self.assertGreaterEqual(
                    _contrast_ratio(tokens["primaryColor"], "#FFFFFF"),
                    AA_NORMAL_TEXT_CONTRAST,
                )

    def test_links_and_code_are_readable_in_both_modes(self) -> None:
        theme = self.config["theme"]
        for mode in ("light", "dark"):
            tokens = theme[mode]
            with self.subTest(theme=mode, surface="links"):
                self.assertGreaterEqual(
                    _contrast_ratio(tokens["linkColor"], tokens["backgroundColor"]),
                    AA_NORMAL_TEXT_CONTRAST,
                )
            with self.subTest(theme=mode, surface="code"):
                self.assertGreaterEqual(
                    _contrast_ratio(
                        tokens["codeTextColor"], tokens["codeBackgroundColor"]
                    ),
                    AA_NORMAL_TEXT_CONTRAST,
                )


if __name__ == "__main__":
    unittest.main()
