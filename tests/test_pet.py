"""Focused tests for Water Buddy's standalone hydration-pet domain."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta

from water_buddy.pet import (
    ACCESSORIES,
    DEFAULT_PET_NAME,
    LEVEL_XP_THRESHOLDS,
    MAX_LEVEL,
    PET_SPECIES,
    award_hydration_xp,
    care_for_pet,
    daily_quest_summary,
    daily_quests,
    default_pet_state,
    equip_accessory,
    normalize_pet_state,
    pet_snapshot,
    rename_pet,
    revoke_hydration_xp,
)


def app_data(now: datetime) -> dict:
    return {
        "profile": {"pet": default_pet_state(now)},
        "daily_records": {
            now.date().isoformat(): {
                "goal_ml": 2200,
                "intake_ml": 0,
                "entries": [],
            }
        },
    }


class PetStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 9, 0)

    def test_default_is_original_and_independent(self) -> None:
        first = default_pet_state(self.now)
        second = default_pet_state(self.now)
        self.assertEqual(first["name"], DEFAULT_PET_NAME)
        self.assertEqual(first["species"], PET_SPECIES)
        self.assertEqual(first["level"], 1)
        self.assertEqual(first["evolution_stage"], "dewdrop")
        first["care"]["last_actions"]["play"] = "changed"
        self.assertNotIn("play", second["care"]["last_actions"])

    def test_normalize_sanitizes_and_derives_progress(self) -> None:
        normalized = normalize_pet_state(
            {
                "name": "  Bubble   Buddy  ",
                "species": "Impostor",
                "xp": 185,
                "level": 99,
                "energy": 120,
                "happiness": -10,
                "equipped_accessory": "star_shell",
                "rewarded_events": {"bad": "not a record"},
            },
            self.now,
        )
        self.assertEqual(normalized["name"], "Bubble Buddy")
        self.assertEqual(normalized["species"], PET_SPECIES)
        self.assertEqual(normalized["level"], 4)
        self.assertEqual(normalized["evolution_stage"], "rippleling")
        self.assertEqual(normalized["energy"], 100)
        self.assertEqual(normalized["happiness"], 0)
        self.assertEqual(normalized["equipped_accessory"], "none")
        self.assertEqual(normalized["rewarded_events"], {})

    def test_snapshot_applies_decay_without_mutating_persisted_state(self) -> None:
        data = app_data(self.now)
        later = self.now + timedelta(hours=5)
        snapshot = pet_snapshot(data, later)
        self.assertAlmostEqual(snapshot["energy"], 83.0)
        self.assertAlmostEqual(snapshot["happiness"], 82.4)
        self.assertEqual(data["profile"]["pet"]["energy"], 86.0)
        self.assertEqual(
            data["profile"]["pet"]["last_updated_at"],
            self.now.isoformat(timespec="seconds"),
        )
        self.assertEqual(snapshot["evolution_name"], "Dewdrop")
        self.assertIn("seafoam_bow", {item["id"] for item in snapshot["available_accessories"]})


class HydrationRewardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 10, 0)
        self.data = app_data(self.now)

    def test_event_id_makes_award_idempotent(self) -> None:
        first = award_hydration_xp(self.data, 250, "water-entry-1", self.now)
        duplicate = award_hydration_xp(self.data, 250, "water-entry-1", self.now)
        self.assertTrue(first["awarded"])
        self.assertEqual(first["xp_awarded"], 6)
        self.assertFalse(duplicate["awarded"])
        self.assertEqual(duplicate["reason"], "duplicate_event")
        self.assertEqual(pet_snapshot(self.data, self.now)["xp"], 6)

    def test_automatic_event_key_blocks_same_second_double_reward(self) -> None:
        first = award_hydration_xp(self.data, 500, now=self.now)
        duplicate = award_hydration_xp(self.data, 500, now=self.now)
        self.assertTrue(first["awarded"])
        self.assertFalse(duplicate["awarded"])

    def test_hydration_xp_has_daily_cap_and_drives_evolution(self) -> None:
        results = [
            award_hydration_xp(self.data, 1000, f"entry-{index}", self.now)
            for index in range(6)
        ]
        snapshot = pet_snapshot(self.data, self.now)
        self.assertEqual(sum(result["xp_awarded"] for result in results), 80)
        self.assertEqual(snapshot["xp"], 80)
        self.assertEqual(snapshot["level"], 2)
        self.assertEqual(snapshot["daily_activity"]["hydration_xp"], 80)
        self.assertEqual(results[-1]["reason"], "daily_cap")

    def test_revoke_is_symmetric_and_cannot_be_repeated(self) -> None:
        award = award_hydration_xp(self.data, 1000, "undo-me", self.now)
        revoked = revoke_hydration_xp(self.data, 1000, "undo-me", self.now)
        repeated = revoke_hydration_xp(self.data, 1000, "undo-me", self.now)
        self.assertEqual(award["xp_awarded"], 20)
        self.assertTrue(revoked["revoked"])
        self.assertEqual(revoked["xp_revoked"], 20)
        self.assertFalse(repeated["revoked"])
        self.assertEqual(pet_snapshot(self.data, self.now)["xp"], 0)

    def test_invalid_hydration_amount_is_rejected(self) -> None:
        for amount in (0, -1, 5001, True):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                award_hydration_xp(self.data, amount, now=self.now)


class PetCareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 9, 0)
        self.data = app_data(self.now)

    def test_care_action_applies_then_enforces_cooldown(self) -> None:
        first = care_for_pet(self.data, "play", self.now)
        blocked = care_for_pet(self.data, "play", self.now + timedelta(minutes=10))
        ready = care_for_pet(self.data, "play", self.now + timedelta(minutes=45))
        self.assertTrue(first["applied"])
        self.assertEqual(first["xp_awarded"], 5)
        self.assertFalse(blocked["applied"])
        self.assertEqual(blocked["reason"], "cooldown")
        self.assertIsNotNone(blocked["retry_at"])
        self.assertTrue(ready["applied"])

    def test_daily_action_limit_prevents_clock_based_farming(self) -> None:
        for index in range(4):
            result = care_for_pet(
                self.data,
                "play",
                self.now + timedelta(minutes=45 * index),
            )
            self.assertTrue(result["applied"])
        blocked = care_for_pet(self.data, "play", self.now + timedelta(minutes=180))
        self.assertFalse(blocked["applied"])
        self.assertEqual(blocked["reason"], "daily_limit")

    def test_unknown_action_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            care_for_pet(self.data, "feed-cookies", self.now)


class PetCustomizationAndQuestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 14, 0)
        self.data = app_data(self.now)

    def test_rename_and_accessory_level_gate(self) -> None:
        renamed = rename_pet(self.data, "  Misty  ")
        self.assertEqual(renamed["name"], "Misty")
        with self.assertRaises(ValueError):
            rename_pet(self.data, "   ")
        with self.assertRaises(ValueError):
            equip_accessory(self.data, "sunny_visor")

        self.data["profile"]["pet"]["xp"] = 180
        equipped = equip_accessory(self.data, "sunny_visor")
        self.assertEqual(equipped["level"], 4)
        self.assertEqual(equipped["equipped_accessory"], "sunny_visor")

    def test_daily_quests_use_water_record_and_pet_care(self) -> None:
        record = self.data["daily_records"][self.now.date().isoformat()]
        record["intake_ml"] = 600
        record["goal_ml"] = 1000
        record["entries"] = [{"amount_ml": 200}] * 3
        care_for_pet(self.data, "encourage", self.now)

        quest_map = {quest["id"]: quest for quest in daily_quests(self.data, self.now)}
        self.assertTrue(quest_map["first_sip"]["complete"])
        self.assertTrue(quest_map["steady_sips"]["complete"])
        self.assertFalse(quest_map["daily_goal"]["complete"])
        self.assertAlmostEqual(quest_map["daily_goal"]["progress"], 0.6)
        self.assertTrue(quest_map["buddy_time"]["complete"])

        summary = daily_quest_summary(self.data, self.now)
        self.assertEqual(summary["completed"], 3)
        self.assertEqual(summary["total"], 4)
        self.assertAlmostEqual(summary["progress"], 0.75)


class PetOutfitProgressionTests(unittest.TestCase):
    """Protect the durable outfit catalog and its level boundaries."""

    def setUp(self) -> None:
        self.now = datetime(2026, 8, 7, 16, 0)

    def test_catalog_preserves_originals_and_adds_exact_outfit_contract(self) -> None:
        original_accessories = {
            "none": {
                "id": "none",
                "name": "No accessory",
                "icon": "block",
                "min_level": 1,
            },
            "seafoam_bow": {
                "id": "seafoam_bow",
                "name": "Seafoam bow",
                "icon": "ribbon",
                "min_level": 2,
            },
            "sunny_visor": {
                "id": "sunny_visor",
                "name": "Sunny visor",
                "icon": "eyeglasses",
                "min_level": 4,
            },
            "coral_crown": {
                "id": "coral_crown",
                "name": "Coral crown",
                "icon": "crown",
                "min_level": 7,
            },
            "star_shell": {
                "id": "star_shell",
                "name": "Star shell",
                "icon": "star",
                "min_level": 10,
            },
        }
        for accessory_id, expected in original_accessories.items():
            with self.subTest(accessory=accessory_id):
                self.assertEqual(ACCESSORIES[accessory_id], expected)

        self.assertEqual(
            ACCESSORIES["samurai_fit"],
            {
                "id": "samurai_fit",
                "name": "Samurai fit",
                "icon": "swords",
                "min_level": 10,
            },
        )
        self.assertEqual(
            ACCESSORIES["cyborg_fit"],
            {
                "id": "cyborg_fit",
                "name": "Cyborg fit",
                "icon": "memory",
                "min_level": 15,
            },
        )
        self.assertEqual(
            ACCESSORIES["cool_guy_fit"],
            {
                "id": "cool_guy_fit",
                "name": "Cool guy fit",
                "icon": "mode_cool",
                "min_level": 20,
            },
        )

    def test_level_curve_preserves_one_through_ten_and_reaches_twenty(self) -> None:
        self.assertEqual(
            LEVEL_XP_THRESHOLDS[:10],
            (0, 40, 100, 180, 280, 400, 550, 730, 940, 1180),
        )
        self.assertEqual(
            LEVEL_XP_THRESHOLDS[10:],
            (1450, 1750, 2080, 2440, 2830, 3250, 3700, 4180, 4690, 5230),
        )
        self.assertEqual(MAX_LEVEL, 20)
        increments = [
            later - earlier
            for earlier, later in zip(
                LEVEL_XP_THRESHOLDS,
                LEVEL_XP_THRESHOLDS[1:],
            )
        ]
        self.assertTrue(all(increment > 0 for increment in increments))
        self.assertEqual(increments[9:], list(range(270, 541, 30)))

    def test_outfits_unlock_exactly_at_required_level_boundaries(self) -> None:
        boundaries = (
            ("samurai_fit", "Samurai fit", 10),
            ("cyborg_fit", "Cyborg fit", 15),
            ("cool_guy_fit", "Cool guy fit", 20),
        )
        for accessory_id, display_name, required_level in boundaries:
            with self.subTest(accessory=accessory_id, boundary="locked"):
                data = app_data(self.now)
                threshold = LEVEL_XP_THRESHOLDS[required_level - 1]
                data["profile"]["pet"]["xp"] = threshold - 1
                locked_snapshot = pet_snapshot(data, self.now)
                self.assertEqual(locked_snapshot["level"], required_level - 1)
                locked_item = next(
                    item
                    for item in locked_snapshot["available_accessories"]
                    if item["id"] == accessory_id
                )
                self.assertFalse(locked_item["unlocked"])
                with self.assertRaises(ValueError) as raised:
                    equip_accessory(data, accessory_id)
                self.assertEqual(
                    str(raised.exception),
                    f"{display_name} unlocks at level {required_level}.",
                )

            with self.subTest(accessory=accessory_id, boundary="unlocked"):
                data = app_data(self.now)
                data["profile"]["pet"]["xp"] = threshold
                equipped = equip_accessory(data, accessory_id)
                self.assertEqual(equipped["level"], required_level)
                self.assertEqual(equipped["equipped_accessory"], accessory_id)
                self.assertIn(accessory_id, equipped["unlocked_accessories"])

    def test_level_ten_keeps_star_shell_and_adds_samurai_fit(self) -> None:
        data = app_data(self.now)
        data["profile"]["pet"]["xp"] = LEVEL_XP_THRESHOLDS[9]
        snapshot = pet_snapshot(data, self.now)
        self.assertEqual(snapshot["level"], 10)
        self.assertIn("star_shell", snapshot["unlocked_accessories"])
        self.assertIn("samurai_fit", snapshot["unlocked_accessories"])

    def test_max_level_snapshot_has_stable_terminal_semantics(self) -> None:
        data = app_data(self.now)
        data["profile"]["pet"]["xp"] = LEVEL_XP_THRESHOLDS[-1]
        snapshot = pet_snapshot(data, self.now)
        self.assertEqual(snapshot["level"], 20)
        self.assertTrue(snapshot["is_max_level"])
        self.assertEqual(snapshot["xp_to_next_level"], 0)
        self.assertEqual(snapshot["xp_for_next_level"], 0)
        self.assertEqual(snapshot["level_progress"], 1.0)
        self.assertIsNone(snapshot["next_evolution"])
        self.assertEqual(snapshot["evolution_stage"], "aqualume")
        self.assertIn("cool_guy_fit", snapshot["unlocked_accessories"])

        data["profile"]["pet"]["xp"] = 1_000_000
        capped_snapshot = pet_snapshot(data, self.now)
        self.assertEqual(capped_snapshot["level"], MAX_LEVEL)
        self.assertTrue(capped_snapshot["is_max_level"])

    def test_outfit_survives_json_round_trip_and_normalization(self) -> None:
        persisted = default_pet_state(self.now)
        persisted["xp"] = LEVEL_XP_THRESHOLDS[14]
        persisted["equipped_accessory"] = " Cyborg-Fit "
        round_tripped = json.loads(json.dumps(persisted))

        normalized = normalize_pet_state(round_tripped, self.now)
        self.assertEqual(normalized["level"], 15)
        self.assertEqual(normalized["equipped_accessory"], "cyborg_fit")
        renormalized = normalize_pet_state(normalized, self.now)
        self.assertEqual(renormalized, normalized)

        legacy = default_pet_state(self.now)
        legacy["xp"] = LEVEL_XP_THRESHOLDS[9]
        legacy["equipped_accessory"] = "star_shell"
        self.assertEqual(
            normalize_pet_state(legacy, self.now)["equipped_accessory"],
            "star_shell",
        )

        too_early = dict(round_tripped)
        too_early["xp"] = LEVEL_XP_THRESHOLDS[13]
        self.assertEqual(
            normalize_pet_state(too_early, self.now)["equipped_accessory"],
            "none",
        )


if __name__ == "__main__":
    unittest.main()
