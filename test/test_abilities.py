"""Tests for the ability/magic system data and PP calculations."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from web.game_session import get_abilities, get_class_abilities, calculate_max_pp
from characterFactory import CharacterFactory


def test_abilities_json_loads():
    abilities = get_abilities()
    assert len(abilities) > 0


def test_all_classes_have_abilities():
    classes = ["Fighter", "Wizard", "Rogue", "Cleric", "Barbarian",
               "Paladin", "Ranger", "Monk", "Bard", "Sorcerer", "Warlock", "Druid"]
    for cls in classes:
        abilities = get_class_abilities(cls, level=20)
        assert len(abilities) >= 5, f"{cls} has only {len(abilities)} abilities, expected at least 5"


def test_every_class_has_free_ability():
    classes = ["Fighter", "Wizard", "Rogue", "Cleric", "Barbarian",
               "Paladin", "Ranger", "Monk", "Bard", "Sorcerer", "Warlock", "Druid"]
    for cls in classes:
        abilities = get_class_abilities(cls, level=1)
        free = [a for a in abilities if a["cost"] == 0]
        assert len(free) >= 1, f"{cls} has no free (0 PP) ability at level 1"


def test_abilities_have_required_fields():
    abilities = get_abilities()
    required = {"name", "classes", "cost", "unlock_level", "description", "target", "attack_method"}
    for ability_id, ability in abilities.items():
        missing = required - set(ability.keys())
        assert not missing, f"Ability '{ability_id}' missing fields: {missing}"


def test_ability_types_valid():
    abilities = get_abilities()
    valid_methods = {"melee_attack", "spell_attack", "spell_save", "auto_hit"}
    valid_targets = {"self", "enemy"}
    for ability_id, ability in abilities.items():
        assert ability["attack_method"] in valid_methods, f"'{ability_id}' has invalid attack_method: {ability['attack_method']}"
        assert ability["target"] in valid_targets, f"'{ability_id}' has invalid target: {ability['target']}"


def test_damage_abilities_have_damage_field():
    abilities = get_abilities()
    for ability_id, ability in abilities.items():
        if ability["target"] == "enemy" and not ability.get("effects"):
            assert "damage" in ability, f"Enemy-targeting ability '{ability_id}' has no damage or effects"


def test_heal_abilities_have_heal_field():
    abilities = get_abilities()
    for ability_id, ability in abilities.items():
        if ability.get("heal"):
            heal = ability["heal"]
            assert "dice_count" in heal, f"Ability '{ability_id}' heal missing dice_count"
            assert "dice_size" in heal, f"Ability '{ability_id}' heal missing dice_size"


def test_pp_calculation_full_caster():
    pp = calculate_max_pp("Wizard", level=5, primary_modifier=3)
    assert pp == 8  # 5 + 3


def test_pp_calculation_half_caster():
    pp = calculate_max_pp("Paladin", level=4, primary_modifier=2)
    assert pp == 4  # 4//2 + 2


def test_pp_calculation_martial():
    pp = calculate_max_pp("Fighter", level=3, primary_modifier=3)
    assert pp == 4  # 3//3 + 3


def test_pp_minimum_is_2():
    pp = calculate_max_pp("Fighter", level=1, primary_modifier=0)
    assert pp == 2  # max(2, 1//3 + 0) = max(2, 0) = 2


def test_unlock_levels_are_reasonable():
    abilities = get_abilities()
    for ability_id, ability in abilities.items():
        assert 1 <= ability["unlock_level"] <= 20, f"'{ability_id}' has unreasonable unlock_level: {ability['unlock_level']}"
        assert 0 <= ability["cost"] <= 5, f"'{ability_id}' has unreasonable cost: {ability['cost']}"


def test_character_has_pp_fields():
    factory = CharacterFactory()
    char = factory.create_character("Test", "Human", "Wizard")
    assert hasattr(char, "power_points")
    assert hasattr(char, "max_power_points")
    assert hasattr(char, "active_effects")


def test_spell_save_abilities_have_save_ability():
    abilities = get_abilities()
    for ability_id, ability in abilities.items():
        if ability["attack_method"] == "spell_save":
            assert "save_ability" in ability, f"spell_save ability '{ability_id}' missing save_ability field"
