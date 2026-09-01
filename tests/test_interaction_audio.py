"""Tests for the no-rerun interface sound component."""

from __future__ import annotations

import importlib
import inspect
import math
import subprocess
import sys
import unittest
from types import ModuleType
from typing import get_type_hints
from unittest.mock import patch


interaction_audio: ModuleType


class InterfaceSoundTests(unittest.TestCase):
    """Verify the Python boundary and the static frontend lifecycle contract."""

    @classmethod
    def setUpClass(cls) -> None:
        # Importing CCv2 outside an AppTest runtime registers against
        # Streamlit's temporary bare-mode manager. Keep that import scoped to
        # this class and evict it afterward so later repository AppTests get a
        # fresh registration in their own runtime manager.
        global interaction_audio
        interaction_audio = importlib.import_module("water_buddy.interaction_audio")

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop("water_buddy.interaction_audio", None)

    def test_public_signature_is_stable(self) -> None:
        signature = inspect.signature(interaction_audio.mount_interface_sounds)
        self.assertEqual(list(signature.parameters), ["enabled", "volume"])
        self.assertEqual(signature.parameters["volume"].default, "Balanced")
        self.assertIs(
            get_type_hints(interaction_audio.mount_interface_sounds)["return"],
            type(None),
        )

    def test_named_presets_mount_only_sanitized_numeric_data(self) -> None:
        cases = {
            " Soft ": 0.016,
            "balanced": 0.03,
            "VIVID": 0.05,
            "Muted": 0.0,
            "mute": 0.0,
            "off": 0.0,
            "silent": 0.0,
        }
        for supplied, expected_gain in cases.items():
            with self.subTest(volume=supplied), patch.object(
                interaction_audio,
                "_INTERFACE_SOUNDS_COMPONENT",
            ) as component:
                result = interaction_audio.mount_interface_sounds(True, supplied)
                self.assertIsNone(result)
                component.assert_called_once_with(
                    key="water-buddy-interface-sounds",
                    data={
                        "enabled": expected_gain > 0.0,
                        "gain": expected_gain,
                    },
                    height=0,
                )

    def test_numeric_volume_is_bounded_by_safe_gain_ceiling(self) -> None:
        for supplied, expected_gain in ((0, 0.0), (0.5, 0.025), (1, 0.05)):
            with self.subTest(volume=supplied), patch.object(
                interaction_audio,
                "_INTERFACE_SOUNDS_COMPONENT",
            ) as component:
                interaction_audio.mount_interface_sounds(True, supplied)
                mounted = component.call_args.kwargs["data"]
                self.assertEqual(mounted["gain"], expected_gain)
                self.assertEqual(mounted["enabled"], expected_gain > 0.0)

    def test_disabled_always_mutes_a_valid_volume(self) -> None:
        with patch.object(
            interaction_audio,
            "_INTERFACE_SOUNDS_COMPONENT",
        ) as component:
            interaction_audio.mount_interface_sounds(False, "Vivid")
        self.assertEqual(
            component.call_args.kwargs["data"],
            {"enabled": False, "gain": 0.05},
        )

    def test_invalid_inputs_are_rejected_before_mount(self) -> None:
        invalid_volumes = (
            "",
            "Maximum",
            -0.01,
            1.01,
            math.nan,
            math.inf,
            True,
            None,
            object(),
        )
        with patch.object(
            interaction_audio,
            "_INTERFACE_SOUNDS_COMPONENT",
        ) as component:
            for volume in invalid_volumes:
                with self.subTest(volume=volume), self.assertRaises(
                    (TypeError, ValueError)
                ):
                    interaction_audio.mount_interface_sounds(True, volume)  # type: ignore[arg-type]
            for enabled in (1, 0, "yes", None):
                with self.subTest(enabled=enabled), self.assertRaises(TypeError):
                    interaction_audio.mount_interface_sounds(  # type: ignore[arg-type]
                        enabled,
                        "Balanced",
                    )
            component.assert_not_called()

    def test_javascript_is_static_deduplicated_and_cleans_up(self) -> None:
        source = interaction_audio._INTERFACE_SOUNDS_JS
        self.assertIn("export default function", source)
        self.assertIn('Symbol.for("water-buddy.interface-sounds.v1")', source)
        self.assertIn('document.addEventListener("pointerup"', source)
        self.assertIn('document.addEventListener("keydown"', source)
        self.assertIn('document.removeEventListener("pointerup"', source)
        self.assertIn('document.removeEventListener("keydown"', source)
        self.assertIn("return cleanup", source)
        self.assertIn("AudioContext", source)
        self.assertIn("createOscillator", source)
        self.assertIn("lastPlayedAt", source)
        self.assertIn("aria-disabled", source)
        for role in ("tab", "option", "checkbox", "radio", "switch"):
            self.assertIn(f"[role='{role}']", source)

        # The component is intentionally one-way: no JS-to-Python bridge, no
        # dynamic content, and no external media or network access.
        for forbidden in (
            "setStateValue",
            "setTriggerValue",
            "window.Streamlit",
            "postMessage",
            "fetch(",
            "XMLHttpRequest",
            "new Audio(",
            "http://",
            "https://",
        ):
            self.assertNotIn(forbidden, source)

    def test_streamlit_app_smoke_across_enabled_and_muted_reruns(self) -> None:
        # Run in a clean interpreter so the module-level component registration
        # occurs inside Streamlit's test runtime, matching a real app startup.
        smoke_program = r'''
from streamlit.testing.v1 import AppTest

source = """
import streamlit as st
from water_buddy.interaction_audio import mount_interface_sounds

enabled = st.toggle("Interface sounds", value=True)
mount_interface_sounds(enabled, "Balanced" if enabled else "Muted")
st.button("Test interaction")
"""

app = AppTest.from_string(source, default_timeout=20).run()
if list(app.exception):
    raise SystemExit(repr(list(app.exception)))
if [button.label for button in app.button] != ["Test interaction"]:
    raise SystemExit("button did not render")
app.toggle[0].set_value(False).run()
if list(app.exception) or app.toggle[0].value:
    raise SystemExit("muted rerun failed")

# AppTest uses a distinct component manager per AppTest object but retains
# Python's module cache. This also models that harness-specific transition.
second_app = AppTest.from_string(source, default_timeout=20).run()
if list(second_app.exception):
    raise SystemExit(repr(list(second_app.exception)))
'''
        completed = subprocess.run(
            [sys.executable, "-c", smoke_program],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
