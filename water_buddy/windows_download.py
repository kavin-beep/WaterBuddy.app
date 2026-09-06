"""Build the small, auditable WaterBuddy Windows shortcut bundle."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

BUNDLE_FILES = (
    "WaterBuddy.ico",
    "Install-WaterBuddy.ps1",
    "Install WaterBuddy.cmd",
    "Remove WaterBuddy.cmd",
    "README.txt",
)


def build_windows_bundle(bundle_directory: Path) -> bytes:
    """Return the Windows shortcut installer files as an in-memory ZIP."""

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for filename in BUNDLE_FILES:
            source = bundle_directory / filename
            archive.writestr(filename, source.read_bytes())
    return output.getvalue()
