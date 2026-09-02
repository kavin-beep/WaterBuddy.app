"""Regression tests for Water Buddy's shared visual system."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

from water_buddy.ui import (
    inject_global_styles,
    mount_page_ambience,
    render_bottle,
    render_pet,
)

_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_CSS_LEAF_RULE = re.compile(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", re.DOTALL)
_CSS_DECLARATION = re.compile(
    r"(?P<name>--[\w-]+|[a-zA-Z-]+)\s*:\s*(?P<value>[^;{}]+);"
)
_CSS_ROUTE_REFERENCE = re.compile(r"var\(\s*(--wb-route-[\w-]+)")


def _normalize_css(value: str) -> str:
    return " ".join(value.split())


def _split_selectors(selector_group: str) -> list[str]:
    """Split a selector list without breaking commas inside :is/:has."""

    selectors: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    for index, character in enumerate(selector_group):
        if quote:
            if character == quote and selector_group[index - 1] != "\\":
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character in "([":
            depth += 1
        elif character in ")]":
            depth = max(0, depth - 1)
        elif character == "," and depth == 0:
            selectors.append(_normalize_css(selector_group[start:index]))
            start = index + 1
    selectors.append(_normalize_css(selector_group[start:]))
    return [selector for selector in selectors if selector]


def _leaf_rules(stylesheet: str) -> list[tuple[str, str]]:
    without_comments = _CSS_COMMENT.sub("", stylesheet)
    rules: list[tuple[str, str]] = []
    for match in _CSS_LEAF_RULE.finditer(without_comments):
        body = match.group("body")
        rules.extend(
            (selector, body) for selector in _split_selectors(match.group("selectors"))
        )
    return rules


def _rule_bodies(stylesheet: str, selector: str) -> list[str]:
    normalized = _normalize_css(selector)
    return [
        body for candidate, body in _leaf_rules(stylesheet) if candidate == normalized
    ]


def _consumer_rules(stylesheet: str, consumer: str) -> list[tuple[str, str]]:
    normalized = _normalize_css(consumer)
    return [
        (selector, body)
        for selector, body in _leaf_rules(stylesheet)
        if selector == normalized or selector.endswith(f" {normalized}")
    ]


def _declarations(body: str) -> dict[str, str]:
    return {
        match.group("name"): _normalize_css(match.group("value"))
        for match in _CSS_DECLARATION.finditer(body)
    }


def _route_references(body: str) -> set[str]:
    return set(_CSS_ROUTE_REFERENCE.findall(body))


def _nested_block(stylesheet: str, header: str) -> str:
    """Return an at-rule body using brace depth instead of a CSS snapshot."""

    match = re.search(rf"{re.escape(header)}\s*\{{", stylesheet)
    if match is None:
        return ""
    start = match.end()
    depth = 1
    for index in range(start, len(stylesheet)):
        if stylesheet[index] == "{":
            depth += 1
        elif stylesheet[index] == "}":
            depth -= 1
            if depth == 0:
                return stylesheet[start:index]
    return ""


def _render_stylesheet(theme: str = "Dark", motion_enabled: bool = True) -> str:
    with patch("water_buddy.ui.st.html") as html:
        inject_global_styles(theme, motion_enabled=motion_enabled)
    return str(html.call_args.args[0])


class PageAmbienceTests(unittest.TestCase):
    VARIANTS = (
        "welcome",
        "home",
        "log",
        "pet",
        "insights",
        "achievements",
        "reminders",
        "coach",
        "profile",
    )
    ROUTE_TOKENS = (
        "--wb-route-primary",
        "--wb-route-secondary",
        "--wb-route-tertiary",
    )
    ROUTE_PALETTES: ClassVar[dict[str, tuple[str, str, str]]] = {
        "welcome": ("#A78BFA", "#FB9A8A", "#5EEAD4"),
        "home": ("#2DD4BF", "#FB7185", "#FBBF24"),
        "log": ("#10B981", "#A3E635", "#F59E0B"),
        "pet": ("#FB7185", "#C084FC", "#FBBF24"),
        "insights": ("#6366F1", "#D946EF", "#5EEAD4"),
        "achievements": ("#FBBF24", "#F97316", "#FB7185"),
        "reminders": ("#F97316", "#F43F5E", "#8B5CF6"),
        "coach": ("#10B981", "#8B5CF6", "#EC4899"),
        "profile": ("#D946EF", "#FB7185", "#F59E0B"),
    }

    def test_every_route_exposes_its_multicolor_palette(self) -> None:
        stylesheet = _render_stylesheet()
        observed_palettes: dict[str, tuple[str, ...]] = {}

        for variant, expected_palette in self.ROUTE_PALETTES.items():
            with self.subTest(variant=variant):
                selector = f".stApp:has(.wb-page-ambience--{variant})"
                bodies = _rule_bodies(stylesheet, selector)
                self.assertEqual(len(bodies), 1)
                declarations = _declarations(bodies[0])
                palette = tuple(
                    declarations.get(token, "").upper() for token in self.ROUTE_TOKENS
                )
                self.assertEqual(palette, expected_palette)
                self.assertEqual(len(set(palette)), len(self.ROUTE_TOKENS))
                observed_palettes[variant] = palette

        self.assertEqual(len(observed_palettes), len(self.VARIANTS))
        self.assertEqual(len(set(observed_palettes.values())), len(self.VARIANTS))
        all_colors = {
            color for palette in observed_palettes.values() for color in palette
        }
        self.assertTrue({"#A3E635", "#F97316", "#EC4899"} <= all_colors)

    def test_each_route_pseudo_layer_consumes_route_palette_tokens(self) -> None:
        stylesheet = _render_stylesheet()
        expected_tokens = set(self.ROUTE_TOKENS)

        for variant in self.VARIANTS:
            with self.subTest(variant=variant):
                consumed: set[str] = set()
                for pseudo_layer in ("::before", "::after"):
                    selector = f".stApp:has(.wb-page-ambience--{variant}){pseudo_layer}"
                    bodies = _rule_bodies(stylesheet, selector)
                    self.assertEqual(len(bodies), 1)
                    references = _route_references(bodies[0])
                    self.assertTrue(references & expected_tokens)
                    consumed.update(references)
                self.assertTrue(expected_tokens <= consumed)

    def test_page_accents_consume_route_tokens_without_semantic_overrides(self) -> None:
        stylesheet = _render_stylesheet()
        marker_classes = {f".wb-page-ambience--{variant}" for variant in self.VARIANTS}
        custom_consumers = (
            ".wb-page-intro",
            ".wb-page-intro::before",
            ".wb-eyebrow",
            ".wb-eyebrow::before",
            ".wb-page-intro__badge",
            ".wb-page-intro__badge::before",
            ".wb-mascot",
            ".wb-pet",
            ".wb-bottle-card",
            ".wb-empty-state",
        )
        native_consumers = (
            '[data-testid="stMetric"]',
            '[data-testid="stExpander"]',
            '[data-testid="stForm"]',
            'div[data-testid="stVerticalBlockBorderWrapper"]',
        )

        for consumer in custom_consumers:
            with self.subTest(consumer=consumer):
                matching_rules = [
                    (selector, body)
                    for selector, body in _consumer_rules(stylesheet, consumer)
                    if _route_references(body)
                ]
                self.assertTrue(matching_rules)

        for consumer in native_consumers:
            with self.subTest(consumer=consumer):
                matching_rules = [
                    (selector, body)
                    for selector, body in _consumer_rules(stylesheet, consumer)
                    if ".stApp:has(:is(" in selector and _route_references(body)
                ]
                self.assertTrue(matching_rules)
                for selector, body in matching_rules:
                    self.assertTrue(
                        marker_classes
                        <= set(re.findall(r"\.wb-page-ambience--[\w-]+", selector))
                    )
                    properties = _declarations(body)
                    self.assertIn("border-color", properties)
                    self.assertIn("--wb-route-primary", _route_references(body))
                    self.assertNotIn("background", properties)
                    self.assertNotIn("background-color", properties)
                    self.assertNotIn("color", properties)
                    self.assertNotIn("button", selector.casefold())
                    self.assertNotIn("stalert", selector.casefold())
                    self.assertNotIn("ststatuswidget", selector.casefold())

    def test_every_page_has_a_scoped_animated_composition(self) -> None:
        with patch("water_buddy.ui.st.html") as html:
            inject_global_styles("Dark")

        stylesheet = html.call_args.args[0]
        for variant in self.VARIANTS:
            with self.subTest(variant=variant):
                self.assertIn(f".wb-page-ambience--{variant}", stylesheet)
        self.assertEqual(stylesheet.count("@keyframes wb-ambience-"), 18)

    def test_marker_is_whitelisted_and_untrusted_text_falls_back(self) -> None:
        class HostileObject:
            def __str__(self) -> str:
                raise AssertionError("untrusted objects must not be converted")

        untrusted = '"><script>alert("ambience")</script>'
        with patch("water_buddy.ui.st.html") as html:
            mount_page_ambience("pet")
            mount_page_ambience(untrusted)
            mount_page_ambience(HostileObject())  # type: ignore[arg-type]

        pet_markup = html.call_args_list[0].args[0]
        fallback_markup = html.call_args_list[1].args[0]
        object_fallback_markup = html.call_args_list[2].args[0]
        self.assertIn("wb-page-ambience--pet", pet_markup)
        self.assertIn("wb-page-ambience--home", fallback_markup)
        self.assertIn("wb-page-ambience--home", object_fallback_markup)
        self.assertNotIn(untrusted, fallback_markup)
        self.assertNotIn("<script>", fallback_markup)
        for call in html.call_args_list:
            self.assertIn(' hidden aria-hidden="true"', call.args[0])
            self.assertEqual(call.kwargs.get("width"), "content")

    def test_motion_preference_disables_page_animation(self) -> None:
        stylesheet = _render_stylesheet("Light", motion_enabled=False)
        self.assertIn(".stApp::before", stylesheet)
        self.assertIn("animation: none !important", stylesheet)

    def test_ambient_layers_remain_noninteractive_and_reduced_motion_safe(self) -> None:
        stylesheet = _render_stylesheet()
        for pseudo_layer in (".stApp::before", ".stApp::after"):
            with self.subTest(pseudo_layer=pseudo_layer):
                safety_rules = [
                    _declarations(body)
                    for body in _rule_bodies(stylesheet, pseudo_layer)
                ]
                self.assertTrue(
                    any(
                        declarations.get("pointer-events") == "none"
                        and declarations.get("z-index") == "-1"
                        for declarations in safety_rules
                    )
                )

        reduced_motion = _nested_block(
            stylesheet,
            "@media (prefers-reduced-motion: reduce)",
        )
        self.assertTrue(reduced_motion)
        self.assertIn(".stApp::before", reduced_motion)
        self.assertIn(".stApp::after", reduced_motion)
        self.assertIn("animation: none !important", reduced_motion)


class ResponsiveContainmentTests(unittest.TestCase):
    def test_global_styles_keep_native_and_custom_content_inside_cards(self) -> None:
        with patch("water_buddy.ui.st.html") as html:
            inject_global_styles("Dark")

        stylesheet = html.call_args.args[0]
        self.assertIn('[data-testid="stHorizontalBlock"]', stylesheet)
        self.assertIn("overflow-wrap: anywhere", stylesheet)
        self.assertIn("white-space: normal !important", stylesheet)
        self.assertIn("@container (max-width: 36rem)", stylesheet)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", stylesheet)


class ThemeVariantTests(unittest.TestCase):
    def test_light_modes_use_dark_text_and_dark_modes_use_white_text(self) -> None:
        expected = {
            "Light": "--wb-ink: #10213D;",
            "Japanese": "--wb-ink: #211A17;",
            "Dark": "--wb-ink: #FFFFFF;",
            "Cyber": "--wb-ink: #FFFFFF;",
        }
        for theme, token in expected.items():
            with self.subTest(theme=theme):
                self.assertIn(token, _render_stylesheet(theme))

    def test_japanese_and_cyber_have_distinct_visual_signatures(self) -> None:
        japanese = _render_stylesheet("Japanese")
        cyber = _render_stylesheet("Cyber")
        self.assertIn("#B4232E", japanese)
        self.assertIn("#F7F1E6", japanese)
        self.assertIn("#00F5FF", cyber)
        self.assertIn("2.75rem 2.75rem", cyber)

    def test_each_theme_owns_its_box_colors(self) -> None:
        expected_surfaces = {
            "Light": ("#FFFFFF", "#F8FAFE"),
            "Dark": ("#09152C", "#0B1933"),
            "Japanese": ("#FFFDF8", "#FBF6EC"),
            "Cyber": ("#080D19", "#071220"),
        }
        for theme, (surface, field) in expected_surfaces.items():
            with self.subTest(theme=theme):
                stylesheet = _render_stylesheet(theme)
                self.assertIn(f"--wb-surface: {surface};", stylesheet)
                self.assertIn(f"--wb-field: {field};", stylesheet)
                self.assertIn(
                    "background-color: var(--wb-surface) !important;",
                    stylesheet,
                )
                self.assertIn(
                    "background-color: var(--wb-field) !important;",
                    stylesheet,
                )

    def test_shell_does_not_consult_streamlit_theme(self) -> None:
        shell = (Path(__file__).resolve().parents[1] / "streamlit_app.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("st.context.theme", shell)


class BottleAndPetInteractionTests(unittest.TestCase):
    def test_over_goal_bottle_remains_full_and_complete(self) -> None:
        with patch("water_buddy.ui.st.html") as html:
            render_bottle(1.25, 2750, 2200)

        markup = html.call_args.args[0]
        self.assertIn("wb-bottle-card--complete", markup)
        self.assertIn("--wb-level: 100.00%", markup)
        self.assertIn("Goal locked in", markup)

    def test_pet_character_is_keyboard_clickable_and_reacts(self) -> None:
        with patch("water_buddy.ui.st.html") as html:
            render_pet({"name": "Ripple"}, 0.75)

        markup = html.call_args.args[0]
        self.assertIn('class="wb-pet__tap-target"', markup)
        self.assertIn('aria-label="Pet Ripple for a happy reaction"', markup)
        self.assertIn("Boop! You found my happy dance.", markup)


class PetCostumeRenderTests(unittest.TestCase):
    def test_milestone_outfits_render_fixed_safe_costume_classes(self) -> None:
        outfits = {
            "samurai_fit": "wb-accessory-samurai",
            "cyborg_fit": "wb-accessory-cyborg",
            "cool_guy_fit": "wb-accessory-cool-guy",
        }

        for accessory_id, expected_class in outfits.items():
            with (
                self.subTest(accessory=accessory_id),
                patch("water_buddy.ui.st.html") as html,
            ):
                render_pet({"equipped_accessory": accessory_id}, 0.75)
                markup = html.call_args.args[0]
                self.assertIn(expected_class, markup)
                self.assertEqual(markup.count("wb-pet__gear wb-pet__gear--"), 3)

    def test_untrusted_accessory_text_never_enters_pet_markup(self) -> None:
        untrusted = '"><script>alert("wardrobe")</script>'
        with patch("water_buddy.ui.st.html") as html:
            render_pet({"equipped_accessory": untrusted}, 0.5)

        markup = html.call_args.args[0]
        self.assertIn("wb-accessory-none", markup)
        self.assertNotIn(untrusted, markup)
        self.assertNotIn("<script>", markup)


if __name__ == "__main__":
    unittest.main()
