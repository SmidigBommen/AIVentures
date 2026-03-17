"""Battle system integration tests — engine combat + domain objects together."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from characterFactory import CharacterFactory
from monsterFactory import MonsterFactory
from dice import Dice
from character import WeaponSlot
from engine.combat import (
    resolve_weapon_attack, get_weapon_attack_modifier,
    roll_initiative, monster_turn_action,
)
from engine.combatant import CombatantState


class TestInitiative:
    def setup_method(self):
        self._orig = Dice.roll_d20

    def teardown_method(self):
        Dice.roll_d20 = self._orig

    def test_initiative_returns_two_values(self):
        a, b = roll_initiative(2, -1)
        assert isinstance(a, int)
        assert isinstance(b, int)

    def test_initiative_includes_dex_mod(self):
        Dice.roll_d20 = lambda: 10
        a, b = roll_initiative(3, -1)
        assert a == 13  # 10 + 3
        assert b == 9   # 10 + (-1)


class TestPlayerAttackWithCharacter:
    """Test attack resolution using actual Character and Monster objects."""

    def setup_method(self):
        self._orig_d20 = Dice.roll_d20
        self._orig_roll = Dice.roll
        cf = CharacterFactory()
        mf = MonsterFactory()
        self.character = cf.create_character("Hero", "Human", "Fighter")
        self.monster = mf.create_monster("Goblin", "Goblin", "Ranger", 1, "Shortbow")
        # Equip a weapon so the character has something to attack with
        from weaponFactory import WeaponFactory
        wf = WeaponFactory()
        sword = wf.get_weapon_by_name("Longsword")
        self.character.equip_weapon(sword, WeaponSlot.MAIN_HAND)

    def teardown_method(self):
        Dice.roll_d20 = self._orig_d20
        Dice.roll = self._orig_roll

    def test_hit_deals_damage(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: size  # max damage
        weapon = self.character.weapon_slots[WeaponSlot.MAIN_HAND]
        ability_mod = self.character.get_attack_modifier(weapon)
        result = resolve_weapon_attack(
            attacker_mod=ability_mod,
            attacker_prof=self.character.proficiency_bonus,
            target_ac=self.monster.armor_class,
            damage_dice_count=weapon.damage_dice_count,
            damage_die=weapon.damage_die,
        )
        assert result["hit"] is True
        assert result["damage"] > 0

    def test_miss_deals_no_damage(self):
        Dice.roll_d20 = lambda: 1
        weapon = self.character.weapon_slots[WeaponSlot.MAIN_HAND]
        ability_mod = self.character.get_attack_modifier(weapon)
        result = resolve_weapon_attack(
            attacker_mod=ability_mod,
            attacker_prof=self.character.proficiency_bonus,
            target_ac=99,  # impossible to hit
            damage_dice_count=weapon.damage_dice_count,
            damage_die=weapon.damage_die,
        )
        assert result["hit"] is False
        assert result["damage"] == 0


class TestMonsterAttackWithCombatant:
    """Test monster attacks using CombatantState (the web battle representation)."""

    def setup_method(self):
        self._orig_d20 = Dice.roll_d20
        self._orig_roll = Dice.roll
        mf = MonsterFactory()
        monster = mf.create_monster("Orc", "Orc", "Fighter", 2, "Handaxe")
        self.combatant = CombatantState.from_monster(monster)

    def teardown_method(self):
        Dice.roll_d20 = self._orig_d20
        Dice.roll = self._orig_roll

    def test_monster_attack_uses_correct_modifier(self):
        mod = get_weapon_attack_modifier(
            self.combatant.str_mod, self.combatant.dex_mod,
            self.combatant.weapon.properties)
        # Handaxe is not finesse or ammunition, so should use STR
        assert mod == self.combatant.str_mod

    def test_monster_hit_deals_damage(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: size
        mod = get_weapon_attack_modifier(
            self.combatant.str_mod, self.combatant.dex_mod,
            self.combatant.weapon.properties)
        result = resolve_weapon_attack(
            attacker_mod=mod,
            attacker_prof=self.combatant.proficiency,
            target_ac=10,
            damage_dice_count=self.combatant.weapon.damage_dice_count,
            damage_die=self.combatant.weapon.damage_die,
        )
        assert result["hit"] is True
        assert result["damage"] >= 1


class TestMonsterAI:
    def test_action_distribution(self):
        """Over many calls, monster should attack ~70% and defend ~30%."""
        import random
        random.seed(42)
        actions = [monster_turn_action() for _ in range(1000)]
        attack_pct = actions.count("attack") / len(actions)
        assert 0.60 < attack_pct < 0.80  # allow some variance


class TestVictoryDetection:
    """Test is_alive() which determines victory/defeat."""

    def test_alive_with_hp(self):
        cf = CharacterFactory()
        char = cf.create_character("Hero", "Human", "Fighter")
        assert char.is_alive() is True

    def test_dead_at_zero_hp(self):
        cf = CharacterFactory()
        char = cf.create_character("Hero", "Human", "Fighter")
        char.current_hit_points = 0
        assert char.is_alive() is False

    def test_monster_alive(self):
        mf = MonsterFactory()
        monster = mf.create_monster("Goblin", "Goblin", "Fighter", 1, "Club")
        assert monster.is_alive() is True

    def test_monster_dead(self):
        mf = MonsterFactory()
        monster = mf.create_monster("Goblin", "Goblin", "Fighter", 1, "Club")
        monster.current_hit_points = 0
        assert monster.is_alive() is False

    def test_combatant_state_hp_tracks_damage(self):
        """CombatantState.hp can be reduced and checked."""
        cs = CombatantState(name="Orc", hp=20, max_hp=20)
        cs.hp -= 15
        assert cs.hp == 5
        cs.hp = 0
        assert cs.hp == 0
