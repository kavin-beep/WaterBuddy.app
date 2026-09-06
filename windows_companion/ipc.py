"""Loopback-only control channel used by Profile and repeated launches."""

from __future__ import annotations

import socket

HOST = "127.0.0.1"
PORT = 47623
COMMANDS = frozenset({"SHOW_MASCOT", "OPEN_HOME", "FOCUS_HOME", "HIDE_MASCOT", "RELOAD_PROFILE", "SHUTDOWN"})


def send_command(command: str, timeout: float = 0.25) -> bool:
    if command not in COMMANDS:
        raise ValueError("Untrusted companion command")
    try:
        with socket.create_connection((HOST, PORT), timeout=timeout) as connection:
            connection.sendall((command + "\n").encode("ascii"))
        return True
    except OSError:
        return False

