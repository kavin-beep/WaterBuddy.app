"""Subtle, synthesized feedback sounds for Water Buddy interactions.

The component contains trusted, static JavaScript only. It never sends browser
events back to Python, so clicking the interface cannot cause a Streamlit
rerun. Mount it once in the shared application shell.
"""

from __future__ import annotations

import math
import threading
from numbers import Real
from typing import Final

import streamlit as st
from streamlit.components.v2.get_bidi_component_manager import (
    get_bidi_component_manager,
)
from streamlit.runtime import Runtime


_MAX_GAIN: Final[float] = 0.05
_COMPONENT_NAME: Final[str] = "water_buddy_interface_sounds"
_REGISTRATION_LOCK: Final[threading.Lock] = threading.Lock()
_VOLUME_GAINS: Final[dict[str, float]] = {
    "soft": 0.016,
    "balanced": 0.03,
    "vivid": _MAX_GAIN,
    "mute": 0.0,
    "muted": 0.0,
    "off": 0.0,
    "silent": 0.0,
}

_INTERFACE_SOUNDS_JS: Final[str] = r"""
const REGISTRY_KEY = Symbol.for("water-buddy.interface-sounds.v1")

export default function interfaceSounds(component) {
  const owner = Symbol("water-buddy-interface-sounds-owner")
  const previous = globalThis[REGISTRY_KEY]
  // A rerun can mount a replacement before the old renderer is unmounted.
  // Retire the previous listener first, while the owner token keeps its later
  // cleanup callback from removing this new instance.
  if (previous && typeof previous.cleanup === "function") {
    previous.cleanup()
  }

  const rawData = component && component.data ? component.data : {}
  const requestedGain = Number(rawData.gain)
  const gain = Number.isFinite(requestedGain)
    ? Math.max(0, Math.min(0.05, requestedGain))
    : 0
  const enabled = rawData.enabled === true && gain > 0

  let disposed = false
  let audioContext = null
  let lastGlobalAt = -Infinity
  const lastPlayedAt = new WeakMap()

  const selector = [
    "button",
    "a[href]",
    "summary",
    "select",
    "input[type='button']",
    "input[type='submit']",
    "input[type='reset']",
    "input[type='checkbox']",
    "input[type='radio']",
    "input[type='range']",
    "[role='button']",
    "[role='link']",
    "[role='tab']",
    "[role='option']",
    "[role='checkbox']",
    "[role='radio']",
    "[role='switch']",
    "[role='slider']",
    "[role='menuitem']",
    "[role='menuitemcheckbox']",
    "[role='menuitemradio']",
    "[data-baseweb='select']",
    "[data-baseweb='tab']",
    "[data-baseweb='checkbox']",
    "[data-baseweb='radio']"
  ].join(",")

  function findControl(event) {
    const path = typeof event.composedPath === "function"
      ? event.composedPath()
      : [event.target]

    for (const node of path) {
      if (!(node instanceof Element)) continue
      if (node.matches(selector)) return node

      const closest = node.closest(selector)
      if (closest) return closest

      const label = node.closest("label")
      if (label && label.querySelector(
        "input[type='checkbox'], input[type='radio']"
      )) {
        return label
      }
    }
    return null
  }

  function isDisabled(control) {
    if (!control || !control.isConnected) return true
    if (control.matches(":disabled, [disabled], [aria-disabled='true']")) {
      return true
    }
    if (control.closest("[inert], fieldset:disabled, [aria-disabled='true']")) {
      return true
    }
    const nestedInput = control.querySelector(
      "input[type='checkbox'], input[type='radio'], input[type='range']"
    )
    return Boolean(nestedInput && nestedInput.disabled)
  }

  function keyboardActivates(event, control) {
    if (event.repeat || event.altKey || event.ctrlKey || event.metaKey) return false
    if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
      return true
    }
    const isDirectionalControl = control.matches(
      "select, [role='tab'], [role='option'], [role='radio'], " +
      "[role='menuitemradio'], [data-baseweb='select']"
    )
    return isDirectionalControl && [
      "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"
    ].includes(event.key)
  }

  function toneShape(control) {
    if (control.matches(
      "a[href], [role='link'], [role='tab'], [role='option'], " +
      "[data-baseweb='select'], select"
    )) {
      return [570, 650, 0.047]
    }
    if (control.matches(
      "input[type='checkbox'], input[type='radio'], [role='checkbox'], " +
      "[role='radio'], [role='switch'], label"
    )) {
      return [440, 525, 0.052]
    }
    return [505, 590, 0.043]
  }

  function scheduleTone(control) {
    if (disposed) return
    const AudioContextClass = globalThis.AudioContext || globalThis.webkitAudioContext
    if (!AudioContextClass) return

    try {
      if (!audioContext || audioContext.state === "closed") {
        audioContext = new AudioContextClass()
      }
      const context = audioContext

      const synthesize = () => {
        if (disposed || context.state === "closed") return
        const [startFrequency, endFrequency, duration] = toneShape(control)
        const start = context.currentTime
        const oscillator = context.createOscillator()
        const envelope = context.createGain()

        oscillator.type = "sine"
        oscillator.frequency.setValueAtTime(startFrequency, start)
        oscillator.frequency.exponentialRampToValueAtTime(
          endFrequency,
          start + duration
        )
        envelope.gain.setValueAtTime(0.0001, start)
        envelope.gain.exponentialRampToValueAtTime(gain, start + 0.004)
        envelope.gain.exponentialRampToValueAtTime(0.0001, start + duration)

        oscillator.connect(envelope)
        envelope.connect(context.destination)
        oscillator.addEventListener("ended", () => {
          oscillator.disconnect()
          envelope.disconnect()
        }, { once: true })
        oscillator.start(start)
        oscillator.stop(start + duration + 0.004)
      }

      if (context.state === "suspended") {
        context.resume().then(synthesize).catch(() => {})
      } else {
        synthesize()
      }
    } catch (_) {
      // Sound feedback is optional and must never interrupt the application.
    }
  }

  function handleInteraction(event) {
    if (disposed || !enabled || event.defaultPrevented) return
    if (event.type === "pointerup") {
      if (event.isPrimary === false || event.button !== 0) return
    }

    const control = findControl(event)
    if (!control || isDisabled(control)) return
    if (event.type === "keydown" && !keyboardActivates(event, control)) return

    const now = performance.now()
    const priorForControl = lastPlayedAt.get(control) ?? -Infinity
    // Prevent a physical action from producing duplicate pointer/keyboard
    // feedback while preserving intentionally quick interactions.
    if (now - priorForControl < 110 || now - lastGlobalAt < 32) return
    lastPlayedAt.set(control, now)
    lastGlobalAt = now
    scheduleTone(control)
  }

  function cleanup() {
    if (disposed) return
    disposed = true
    document.removeEventListener("pointerup", handleInteraction, true)
    document.removeEventListener("keydown", handleInteraction, true)
    if (audioContext && audioContext.state !== "closed") {
      audioContext.close().catch(() => {})
    }
    const current = globalThis[REGISTRY_KEY]
    if (current && current.owner === owner) {
      delete globalThis[REGISTRY_KEY]
    }
  }

  globalThis[REGISTRY_KEY] = { owner, cleanup }
  if (enabled) {
    document.addEventListener("pointerup", handleInteraction, true)
    document.addEventListener("keydown", handleInteraction, true)
  }

  return cleanup
}
"""


_INTERFACE_SOUNDS_COMPONENT = st.components.v2.component(
    _COMPONENT_NAME,
    js=_INTERFACE_SOUNDS_JS,
)


def _ensure_runtime_registration() -> None:
    """Repair a runtime registry when an embedding harness swaps runtimes.

    A real Streamlit server owns one component manager shared by all browser
    sessions, so the module-level declaration is sufficient in production.
    ``AppTest`` intentionally creates an isolated manager for every test app
    while retaining Python's import cache. If this module was imported by a
    prior test runtime, copy the same static definition into the active manager
    without declaring a second component or replacing the mount callable.
    """

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
            js=_INTERFACE_SOUNDS_JS,
        )
        manager.register(definition)
        manager.record_api_inputs(_COMPONENT_NAME, None, _INTERFACE_SOUNDS_JS)


def _resolve_gain(volume: str | float) -> float:
    """Convert a public volume value into a bounded Web Audio gain."""

    if isinstance(volume, str):
        normalized = volume.strip().casefold()
        if normalized not in _VOLUME_GAINS:
            raise ValueError(
                "volume must be 'Soft', 'Balanced', 'Vivid', 'Muted', "
                "or a number from 0.0 to 1.0"
            )
        return _VOLUME_GAINS[normalized]

    if isinstance(volume, bool) or not isinstance(volume, Real):
        raise TypeError("volume must be a preset name or a number from 0.0 to 1.0")
    numeric = float(volume)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError("numeric volume must be finite and between 0.0 and 1.0")
    return round(numeric * _MAX_GAIN, 6)


def mount_interface_sounds(
    enabled: bool,
    volume: str | float = "Balanced",
) -> None:
    """Mount document-wide, no-rerun interaction sounds for this app session.

    ``volume`` accepts the safe presets ``"Soft"``, ``"Balanced"``, and
    ``"Vivid"``; ``"Muted"`` (plus ``"Mute"``, ``"Off"``, or ``"Silent"``)
    disables tones. A finite number from 0.0 through 1.0 scales within the same
    safe output ceiling. ``enabled=False`` always mutes the component.

    Call this once per script run in the shared shell, before navigation is
    mounted, so the listener covers both signed-out and signed-in controls.
    """

    if not isinstance(enabled, bool):
        raise TypeError("enabled must be a bool")
    gain = _resolve_gain(volume)
    _ensure_runtime_registration()
    _INTERFACE_SOUNDS_COMPONENT(
        key="water-buddy-interface-sounds",
        data={"enabled": enabled and gain > 0.0, "gain": gain},
        height=0,
    )


__all__ = ["mount_interface_sounds"]
