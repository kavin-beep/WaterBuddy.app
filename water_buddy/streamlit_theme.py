"""Keep Streamlit's host mode aligned with Water Buddy's display theme."""

from __future__ import annotations

import threading
from typing import Final

import streamlit as st
from streamlit.components.v2.get_bidi_component_manager import (
    get_bidi_component_manager,
)
from streamlit.runtime import Runtime

from water_buddy.domain import normalize_theme


_COMPONENT_NAME: Final[str] = "water_buddy_streamlit_theme"
_REGISTRATION_LOCK: Final[threading.Lock] = threading.Lock()
_DARK_THEMES: Final[frozenset[str]] = frozenset({"Dark", "Cyber"})

_STREAMLIT_THEME_JS: Final[str] = r"""
const REGISTRY_KEY = Symbol.for("water-buddy.streamlit-theme.v1")

export default function streamlitThemeSync(component) {
  const previous = globalThis[REGISTRY_KEY]
  if (previous && typeof previous.cleanup === "function") {
    previous.cleanup()
  }

  const rawData = component && component.data ? component.data : {}
  const desiredMode = rawData.mode === "light" ? "light" : "dark"
  const currentMode = rawData.currentMode === "light" ? "light"
    : rawData.currentMode === "dark" ? "dark"
    : ""
  const root = document.documentElement
  const body = document.body
  const timers = new Set()
  let disposed = false
  let openedMenu = false

  // This also covers native inputs and portaled UI if Streamlit's menu is not
  // available (for example, when an embedding host hides the toolbar).
  root.style.colorScheme = desiredMode
  root.dataset.waterBuddyStreamlitTheme = desiredMode
  if (body) {
    body.style.colorScheme = desiredMode
  }

  function schedule(callback, delay) {
    const timer = window.setTimeout(() => {
      timers.delete(timer)
      if (!disposed) callback()
    }, delay)
    timers.add(timer)
  }

  function selectDesiredTheme(attempt = 0) {
    if (disposed) return

    const target = document.querySelector(
      `[data-testid="stMainMenuItem-theme-${desiredMode === "dark" ? "Dark" : "Light"}"]`
    )
    if (target) {
      if (target.getAttribute("aria-checked") !== "true") {
        target.click()
      } else if (openedMenu) {
        document.querySelector('[data-testid="stMainMenuButton"]')?.click()
      }
      openedMenu = false
      return
    }

    const menuButton = document.querySelector('[data-testid="stMainMenuButton"]')
    if (attempt >= 12) return
    if (!menuButton) {
      schedule(() => selectDesiredTheme(attempt + 1), 25)
      return
    }
    if (menuButton.getAttribute("aria-expanded") !== "true") {
      menuButton.click()
      openedMenu = true
    }
    schedule(() => selectDesiredTheme(attempt + 1), 25)
  }

  // Avoid opening Streamlit's menu when its reported mode already matches.
  if (currentMode !== desiredMode) {
    schedule(() => selectDesiredTheme(), 0)
  }

  function cleanup() {
    disposed = true
    for (const timer of timers) window.clearTimeout(timer)
    timers.clear()
  }

  globalThis[REGISTRY_KEY] = { cleanup }
  return cleanup
}
"""


_STREAMLIT_THEME_COMPONENT = st.components.v2.component(
    _COMPONENT_NAME,
    js=_STREAMLIT_THEME_JS,
)


def _ensure_runtime_registration() -> None:
    """Register the static component in real and isolated test runtimes."""

    if not Runtime.exists():
        return
    manager = get_bidi_component_manager()
    if manager.get(_COMPONENT_NAME) is not None:
        return
    with _REGISTRATION_LOCK:
        if manager.get(_COMPONENT_NAME) is not None:
            return
        definition = manager.build_definition_with_validation(
            component_key=_COMPONENT_NAME,
            html=None,
            css=None,
            js=_STREAMLIT_THEME_JS,
        )
        manager.register(definition)
        manager.record_api_inputs(_COMPONENT_NAME, None, _STREAMLIT_THEME_JS)


def streamlit_mode_for(theme: object) -> str:
    """Map Water Buddy's four display themes to a Streamlit host mode."""

    return "dark" if normalize_theme(theme) in _DARK_THEMES else "light"


def _current_streamlit_mode() -> str:
    """Read Streamlit's reported mode without treating it as app authority."""

    current = st.context.theme.get("type")
    return current if current in {"light", "dark"} else ""


def mount_streamlit_theme(theme: object) -> None:
    """Synchronize the current browser session with Water Buddy's theme."""

    desired_mode = streamlit_mode_for(theme)
    _ensure_runtime_registration()
    _STREAMLIT_THEME_COMPONENT(
        key="water-buddy-streamlit-theme",
        data={
            "mode": desired_mode,
            "currentMode": _current_streamlit_mode(),
        },
        height=0,
    )


__all__ = ["mount_streamlit_theme", "streamlit_mode_for"]
