"""Tests for engine.combat — attack resolution, weapon modifiers, rewards."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from engine.combat import (
    get_weapon_attack_modifier,
    resolve_weapon_attack,
    calculate_xp_reward,
    calculate_gold_reward,
    roll_damage,
    attack_roll,
)


class TestWeaponAttackModifier:
    def test_normal_weapon_uses_str(self):
        assert get_weapon_attack_modifier(3, 1, []) == 3

    def test_ranged_weapon_uses_dex(self):
        assert get_weapon_attack_modifier(3, 1, ["ammunition"]) == 1

    def test_finesse_weapon_uses_higher(self):
        assert get_weapon_attack_modifier(1, 3, ["finesse"]) == 3
        assert get_weapon_attack_modifier(4, 2, ["finesse"]) == 4

    def test_finesse_ranged_prefers_ammunition(self):
        """Ammunition check comes first — daggers thrown use DEX."""
        assert get_weapon_attack_modifier(3, 1, ["ammunition", "finesse"]) == 1


class TestResolveWeaponAttack:
    def setup_method(self):
        self._orig_d20 = Dice.roll_d20
        self._orig_roll = Dice.roll

    def teardown_method(self):
        Dice.roll_d20 = self._orig_d20
        Dice.roll = self._orig_roll

    def test_guaranteed_hit(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: size  # max damage
        result = resolve_weapon_attack(
            attacker_mod=3, attacker_prof=2, target_ac=10,
            damage_dice_count=1, damage_die=8)
        assert result["hit"] is True
        assert result["damage"] >= 1

    def test_guaranteed_miss(self):
        Dice.roll_d20 = lambda: 1
        result = resolve_weapon_attack(
            attacker_mod=0, attacker_prof=0, target_ac=20,
            damage_dice_count=1, damage_die=8)
        assert result["hit"] is False
        assert result["damage"] == 0

    def test_exact_hit_on_ac(self):
        """Roll + mods == AC should hit."""
        Dice.roll_d20 = lambda: 10
        Dice.roll = lambda size: 4
        result = resolve_weapon_attack(
            attacker_mod=2, attacker_prof=2, target_ac=14,
            damage_dice_count=1, damage_die=8)
        # 10 + 2 + 2 = 14 == AC 14 => hit
        assert result["hit"] is True
        assert result["attack_roll"] == 14

    def test_attacker_effect_bonus_applied(self):
        Dice.roll_d20 = lambda: 10
        Dice.roll = lambda size: 4
        effects = [{"stat": "attack_bonus", "value": 5, "duration": 1, "source": "buff"}]
        result = resolve_weapon_attack(
            attacker_mod=0, attacker_prof=0, target_ac=14,
            damage_dice_count=1, damage_die=8,
            attacker_effects=effects)
        # 10 + 0 + 0 + 5(effect) = 15 >= 14
        assert result["hit"] is True
        assert result["attack_roll"] == 15

    def test_target_ac_effect_applied(self):
        Dice.roll_d20 = lambda: 10
        target_effects = [{"stat": "ac", "value": 5, "duration": 0, "source": "shield"}]
        result = resolve_weapon_attack(
            attacker_mod=2, attacker_prof=2, target_ac=10,
            damage_dice_count=1, damage_die=8,
            target_effects=target_effects)
        # 10 + 2 + 2 = 14 vs AC 10+5 = 15 => miss
        assert result["hit"] is False
        assert result["target_ac"] == 15

    def test_damage_reduction_applied(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: 4
        target_effects = [{"stat": "damage_reduction", "value": 3, "duration": 0, "source": "armor"}]
        result = resolve_weapon_attack(
            attacker_mod=2, attacker_prof=2, target_ac=10,
            damage_dice_count=1, damage_die=8,
            target_effects=target_effects)
        assert result["hit"] is True
        # raw = 4 + 2 = 6, DR 3, net = 3
        assert result["damage"] == 3

    def test_damage_minimum_is_1(self):
        """Even with huge DR, minimum 1 damage on hit."""
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: 1
        target_effects = [{"stat": "damage_reduction", "value": 100, "duration": 0, "source": "armor"}]
        result = resolve_weapon_attack(
            attacker_mod=0, attacker_prof=0, target_ac=5,
            damage_dice_count=1, damage_die=4,
            target_effects=target_effects)
        assert result["hit"] is True
        assert result["damage"] == 1

    def test_damage_bonus_effect(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: 1
        attacker_effects = [{"stat": "damage_bonus", "value": 10, "duration": 1, "source": "rage"}]
        result = resolve_weapon_attack(
            attacker_mod=0, attacker_prof=0, target_ac=5,
            damage_dice_count=1, damage_die=4,
            attacker_effects=attacker_effects)
        # roll_damage(1, 4, 0, 10) = max(1, 1 + 0 + 10) = 11
        assert result["damage"] == 11

    def test_multi_dice_damage(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: size  # max each die
        result = resolve_weapon_attack(
            attacker_mod=3, attacker_prof=2, target_ac=10,
            damage_dice_count=2, damage_die=6)
        # 2d6 max = 12, + 3 mod = 15
        assert result["damage"] == 15


class TestRollDamage:
    def setup_method(self):
        self._orig = Dice.roll

    def teardown_method(self):
        Dice.roll = self._orig

    def test_minimum_damage_is_1(self):
        Dice.roll = lambda size: 1
        assert roll_damage(1, 6, ability_mod=-5) == 1

    def test_bonus_added(self):
        Dice.roll = lambda size: 3
        assert roll_damage(1, 6, ability_mod=2, bonus=1) == 6  # 3 + 2 + 1


class TestXPReward:
    def test_level_1_fast_kill(self):
        assert calculate_xp_reward(1, 1) == 190  # 100 + 90

    def test_level_5_slow_kill(self):
        assert calculate_xp_reward(5, 15) == 500  # 500 + 0 (capped)

    def test_round_bonus_caps_at_zero(self):
        assert calculate_xp_reward(1, 100) == 100  # no negative bonus


class TestGoldReward:
    def setup_method(self):
        self._orig = Dice.roll_d8

    def teardown_method(self):
        Dice.roll_d8 = self._orig

    def test_gold_formula(self):
        Dice.roll_d8 = lambda: 4
        assert calculate_gold_reward(3) == 19  # 3*5 + 4
