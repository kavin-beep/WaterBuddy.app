"""Windows named-mutex ownership for exactly one companion process."""

from __future__ import annotations

import ctypes
import sys


class SingleInstance:
    def __init__(self, name: str = "Local\\WaterBuddyDesktopPet") -> None:
        self.handle = None
        self.already_running = False
        if sys.platform == "win32":
            self.handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
            self.already_running = ctypes.windll.kernel32.GetLastError() == 183

    def close(self) -> None:
        if self.handle and sys.platform == "win32":
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None

