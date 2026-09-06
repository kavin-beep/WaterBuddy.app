"""Open only allow-listed Water Buddy routes."""

from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import urljoin

APP_URL = os.environ.get("WATER_BUDDY_APP_URL", "https://waterbuddyapp-eqqehr8sj4lxskbvmsxnu9.streamlit.app/").rstrip("/") + "/"
ROUTES = {"home": "home", "reminders": "reminders", "pet": "pet"}


def route_url(route: str) -> str:
    if route not in ROUTES:
        raise ValueError("Unknown Water Buddy route")
    return urljoin(APP_URL, ROUTES[route])


def open_app(route: str = "home") -> None:
    url = route_url(route)
    roots = (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA"))
    chrome = next((Path(root) / r"Google\Chrome\Application\chrome.exe" for root in roots if root and (Path(root) / r"Google\Chrome\Application\chrome.exe").is_file()), None)
    if chrome:
        subprocess.Popen([str(chrome), f"--app={url}", "--window-size=520,760"], close_fds=True)
    else:
        webbrowser.open(url, new=1)

