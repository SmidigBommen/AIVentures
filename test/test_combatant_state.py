"""Tests for engine.combatant — serialization roundtrips and from_monster."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.combatant import CombatantState, WeaponState
from monsterFactory import MonsterFactory


class TestWeaponStateRoundtrip:
    def test_default_roundtrip(self):
        ws = WeaponState()
        d = ws.to_dict()
        ws2 = WeaponState.from_dict(d)
        assert ws2.name == ""
        assert ws2.damage_die == 6
        assert ws2.damage_dice_count == 1
        assert ws2.properties == []

    def test_full_roundtrip(self):
        ws = WeaponState(name="Longsword", damage_die=8, damage_dice_count=1, properties=["versatile"])
        d = ws.to_dict()
        ws2 = WeaponState.from_dict(d)
        assert ws2.name == "Longsword"
        assert ws2.damage_die == 8
        assert ws2.properties == ["versatile"]

    def test_from_dict_handles_missing_fields(self):
        ws = WeaponState.from_dict({})
        assert ws.name == ""
        assert ws.damage_die == 6

    def test_from_weapon_object(self):
        factory = MonsterFactory()
        monster = factory.create_monster("Goblin", "Goblin", "Fighter", 1, "Club")
        ws = WeaponState.from_weapon(monster.weapon)
        assert ws.name == "Club"
        assert ws.damage_die > 0


class TestCombatantStateRoundtrip:
    def test_default_roundtrip(self):
        cs = CombatantState()
        d = cs.to_dict()
        cs2 = CombatantState.from_dict(d)
        assert cs2.name == ""
        assert cs2.hp == 0
        assert cs2.ac == 10
        assert isinstance(cs2.weapon, WeaponState)

    def test_full_roundtrip(self):
        cs = CombatantState(
            name="Gruk", race="Orc", level=5,
            hp=35, max_hp=40, ac=16, base_ac=14,
            str_mod=3, dex_mod=1, proficiency=3,
            weapon=WeaponState(name="Greataxe", damage_die=12, damage_dice_count=1, properties=[]),
            effects=[{"stat": "ac", "value": 2, "duration": 0, "source": "shield"}],
        )
        d = cs.to_dict()
        cs2 = CombatantState.from_dict(d)
        assert cs2.name == "Gruk"
        assert cs2.race == "Orc"
        assert cs2.level == 5
        assert cs2.hp == 35
        assert cs2.max_hp == 40
        assert cs2.ac == 16
        assert cs2.base_ac == 14
        assert cs2.str_mod == 3
        assert cs2.dex_mod == 1
        assert cs2.proficiency == 3
        assert cs2.weapon.name == "Greataxe"
        assert cs2.weapon.damage_die == 12
        assert len(cs2.effects) == 1
        assert cs2.effects[0]["stat"] == "ac"

    def test_from_dict_handles_missing_fields(self):
        cs = CombatantState.from_dict({})
        assert cs.name == ""
        assert cs.ac == 10
        assert cs.weapon.name == ""

    def test_effects_survive_roundtrip(self):
        cs = CombatantState(effects=[
            {"stat": "attack_bonus", "value": 2, "duration": 3, "source": "spell"},
            {"stat": "damage_reduction", "value": 5, "duration": 0, "source": "stoneskin"},
        ])
        d = cs.to_dict()
        cs2 = CombatantState.from_dict(d)
        assert len(cs2.effects) == 2
        assert cs2.effects[1]["stat"] == "damage_reduction"


class TestFromMonster:
    def test_from_monster_preserves_stats(self):
        factory = MonsterFactory()
        monster = factory.create_monster("Gruk", "Orc", "Fighter", 3, "Handaxe")
        cs = CombatantState.from_monster(monster)
        assert cs.name == "Gruk"
        assert cs.race == "Orc"
        assert cs.level == 3
        assert cs.hp == monster.current_hit_points
        assert cs.max_hp == monster.max_hit_points
        assert cs.ac == monster.armor_class
        assert cs.base_ac == monster.base_ac
        assert cs.str_mod == monster.strength_modifier
        assert cs.dex_mod == monster.dexterity_modifier
        assert cs.proficiency == monster.proficiency_bonus
        assert cs.weapon.name == "Handaxe"
        assert cs.effects == []

    def test_from_monster_roundtrips_through_dict(self):
        factory = MonsterFactory()
        monster = factory.create_monster("Shade", "Shadow Wraith", "Fighter", 5, "Club")
        cs = CombatantState.from_monster(monster)
        d = cs.to_dict()
        cs2 = CombatantState.from_dict(d)
        assert cs2.name == cs.name
        assert cs2.hp == cs.hp
        assert cs2.weapon.name == cs.weapon.name


class TestResetAC:
    def test_reset_clears_defend_bonus(self):
        cs = CombatantState(ac=18, base_ac=14, dex_mod=2)
        cs.reset_ac()
        assert cs.ac == 16  # base_ac + dex_mod

    def test_reset_from_lower_ac(self):
        """Edge case: AC somehow lower than base+dex."""
        cs = CombatantState(ac=8, base_ac=12, dex_mod=1)
        cs.reset_ac()
        assert cs.ac == 13
