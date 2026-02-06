import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from monsterFactory import MonsterFactory


def load_json(filename):
    with open(Path(__file__).parent.parent / "json" / filename) as f:
        return json.load(f)


class TestMonsterDataIntegrity:
    """Verify that all monster JSON data is consistent and complete."""

    def setup_method(self):
        self.monster_defaults = load_json("monster_default_values.json")
        self.weapon_catalog = load_json("weapon-catalog.json")
        self.campaign = load_json("campaign.json")

        # Build a flat set of all weapon names across all categories
        self.all_weapons = set()
        for category in self.weapon_catalog.values():
            self.all_weapons.update(category.keys())

    def test_all_races_have_required_fields(self):
        required_fields = [
            "Strength", "Dexterity", "Constitution", "Intelligence",
            "Wisdom", "Charisma", "base_ac", "hit_die",
            "weapons", "class_options", "names", "challenge_rating"
        ]
        for race, data in self.monster_defaults.items():
            for field in required_fields:
                assert field in data, f"{race} missing required field: {field}"

    def test_weapons_reference_valid_catalog_entries(self):
        for race, data in self.monster_defaults.items():
            for weapon in data["weapons"]:
                assert weapon in self.all_weapons, (
                    f"{race} references weapon '{weapon}' not found in weapon-catalog.json"
                )

    def test_names_are_nonempty(self):
        for race, data in self.monster_defaults.items():
            assert len(data["names"]) > 0, f"{race} has an empty names list"

    def test_class_options_are_nonempty(self):
        for race, data in self.monster_defaults.items():
            assert len(data["class_options"]) > 0, f"{race} has empty class_options"

    def test_campaign_monster_types_exist_in_defaults(self):
        for act in self.campaign["acts"]:
            for location in act["locations"]:
                for area in location["areas"]:
                    monster_types = area.get("monster_types", [])
                    for mt in monster_types:
                        assert mt in self.monster_defaults, (
                            f"Area '{area['name']}' references monster type '{mt}' "
                            f"not found in monster_default_values.json"
                        )

    def test_areas_with_encounters_have_monster_types(self):
        for act in self.campaign["acts"]:
            for location in act["locations"]:
                for area in location["areas"]:
                    if area.get("encounters", 0) > 0:
                        assert "monster_types" in area, (
                            f"Area '{area['name']}' has encounters={area['encounters']} "
                            f"but no monster_types defined"
                        )

    def test_hp_calculation_works_for_every_race(self):
        factory = MonsterFactory()
        for race in self.monster_defaults:
            for level in [1, 5, 10]:
                monster = factory.create_monster("Test", race, "Fighter", level, "Club")
                assert monster.max_hit_points >= 1, (
                    f"{race} at level {level} has invalid HP: {monster.max_hit_points}"
                )

    def test_challenge_rating_is_positive_integer(self):
        for race, data in self.monster_defaults.items():
            cr = data["challenge_rating"]
            assert isinstance(cr, int) and cr > 0, (
                f"{race} has invalid challenge_rating: {cr}"
            )

    def test_hit_die_is_valid(self):
        valid_dice = {4, 6, 8, 10, 12, 20}
        for race, data in self.monster_defaults.items():
            assert data["hit_die"] in valid_dice, (
                f"{race} has invalid hit_die: {data['hit_die']}"
            )
