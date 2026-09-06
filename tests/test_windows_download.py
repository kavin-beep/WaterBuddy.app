"""Tests for the downloadable WaterBuddy Windows shortcut bundle."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import unittest
from zipfile import ZipFile

from water_buddy.windows_download import BUNDLE_FILES, build_windows_bundle

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "windows_app"


class WindowsDownloadTests(unittest.TestCase):
    def test_bundle_has_only_expected_flat_files(self) -> None:
        with ZipFile(BytesIO(build_windows_bundle(ASSETS))) as archive:
            self.assertEqual(tuple(archive.namelist()), BUNDLE_FILES)
            self.assertTrue(all("/" not in name and "\\" not in name for name in archive.namelist()))

    def test_installer_creates_app_mode_desktop_shortcut(self) -> None:
        installer = (ASSETS / "Install-WaterBuddy.ps1").read_text(encoding="utf-8")
        self.assertIn("WaterBuddy.lnk", installer)
        self.assertIn("--app=$AppUrl", installer)
        self.assertIn("streamlit.app", installer)

    def test_icon_is_a_windows_icon(self) -> None:
        self.assertEqual((ASSETS / "WaterBuddy.ico").read_bytes()[:4], b"\x00\x00\x01\x00")


if __name__ == "__main__":
    unittest.main()
