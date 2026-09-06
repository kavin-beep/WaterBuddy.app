"""Best-effort local lifecycle control callable from the Streamlit Profile page."""

from __future__ import annotations

import subprocess
from pathlib import Path

from windows_companion.ipc import send_command


def installed_executable(project_root: Path | None = None) -> Path | None:
    root = project_root or Path(__file__).resolve().parents[1]
    candidates = (root / "dist" / "WaterBuddyPet.exe", Path.home() / "AppData" / "Local" / "WaterBuddy" / "WaterBuddyPet.exe")
    return next((path for path in candidates if path.is_file()), None)


def apply_enabled(enabled: bool, profile_path: str | Path) -> str:
    """Notify a running companion, or start an installed local build when enabled."""
    if not enabled:
        return "stopped" if send_command("SHUTDOWN") else "not-running"
    if send_command("SHOW_MASCOT"):
        send_command("RELOAD_PROFILE")
        return "running"
    executable = installed_executable()
    if executable is None:
        return "not-installed"
    subprocess.Popen(
        [str(executable), "--profile", str(Path(profile_path).resolve())],
        cwd=str(executable.parent),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )
    return "started"


def reload_running() -> bool:
    return send_command("RELOAD_PROFILE")

