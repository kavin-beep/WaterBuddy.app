"""Tests for Water Buddy's canonical volume conversions."""

from __future__ import annotations

import unittest

from water_buddy.units import (
    format_volume,
    from_millilitres,
    normalize_units,
    to_millilitres,
    unit_label,
)


class VolumeUnitTests(unittest.TestCase):
    def test_normalizes_supported_imperial_aliases(self) -> None:
        for value in ("oz", "FL OZ", "floz", "fluid ounces"):
            with self.subTest(value=value):
                self.assertEqual(normalize_units(value), "oz")
                self.assertEqual(unit_label(value), "fl oz")
        self.assertEqual(normalize_units("litres"), "l")
        self.assertEqual(unit_label("litres"), "L")
        self.assertEqual(unit_label("ml"), "ml")

    def test_round_trip_is_accurate_to_one_millilitre(self) -> None:
        for amount_ml in (50, 250, 500, 2200, 5000):
            with self.subTest(amount_ml=amount_ml):
                ounces = from_millilitres(amount_ml, "oz")
                self.assertLessEqual(abs(to_millilitres(ounces, "oz") - amount_ml), 1)
        self.assertEqual(to_millilitres(1.5, "litres"), 1500)

    def test_formats_both_display_modes(self) -> None:
        self.assertEqual(format_volume(250, "ml"), "250 ml")
        self.assertEqual(format_volume(250, "oz"), "8.5 fl oz")
        self.assertEqual(format_volume(1500, "litres"), "1.5 L")
        self.assertEqual(format_volume(None, "oz"), "0 fl oz")

    def test_invalid_display_amounts_are_rejected(self) -> None:
        for value in (True, -1, float("nan"), float("inf"), "water"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                to_millilitres(value, "oz")


if __name__ == "__main__":
    unittest.main()
