"""Tests for player class ability resolution (engine/abilities.py)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from characterFactory import CharacterFactory
from engine.abilities import resolve_player_ability
from engine.combatant import CombatantState
from web.game_session import get_abilities


def _monster(**kwargs):
    defaults = dict(name="Grak", race="Orc", level=3, hp=100, max_hp=100, ac=12, base_ac=11)
    defaults.update(kwargs)
    return CombatantState(**defaults)


class TestPlayerAbilities:
    def setup_method(self):
        self._orig_d20, self._orig_roll = Dice.roll_d20, Dice.roll
        self.char = CharacterFactory().create_character("Hero", "Human", "Fighter")
        self.char.power_points = self.char.max_power_points = 10
        self.abilities = get_abilities()

    def teardown_method(self):
        Dice.roll_d20, Dice.roll = self._orig_d20, self._orig_roll

    def test_cannot_afford_returns_none_and_spends_nothing(self):
        self.char.power_points = 0
        monster = _monster()
        assert resolve_player_ability(self.char, self.abilities["action_surge"], monster, [], 3) is None
        assert self.char.power_points == 0
        assert monster.hp == 100

    def test_pp_is_spent(self):
        Dice.roll_d20 = lambda: 15
        resolve_player_ability(self.char, self.abilities["action_surge"], _monster(), [], 3)
        assert self.char.power_points == 10 - self.abilities["action_surge"]["cost"]

    def test_hit_deals_damage(self):
        Dice.roll_d20 = lambda: 15
        Dice.roll = lambda size: 5
        monster = _monster()
        resolve_player_ability(self.char, self.abilities["power_strike"], monster, [], 3)
        # 1d10 (5) + primary mod 3
        assert monster.hp == 92

    def test_critical_hit_doubles_dice(self):
        Dice.roll_d20 = lambda: 20
        Dice.roll = lambda size: 5
        monster = _monster()
        log = resolve_player_ability(self.char, self.abilities["power_strike"], monster, [], 3)
        assert monster.hp == 100 - (10 + 3)
        assert "CRITICAL" in log[0]

    def test_miss_deals_no_damage_and_no_rider(self):
        Dice.roll_d20 = lambda: 2
        monster = _monster(ac=25)
        resolve_player_ability(self.char, self.abilities["poison_strike"], monster, [], 3)
        assert monster.hp == 100
        assert monster.effects == []

    def test_hit_applies_rider_effects(self):
        Dice.roll_d20 = lambda: 15
        monster = _monster()
        resolve_player_ability(self.char, self.abilities["poison_strike"], monster, [], 3)
        assert {e["stat"] for e in monster.effects} == {"ac", "poison"}

    def test_successful_save_halves_damage_and_blocks_rider(self):
        Dice.roll_d20 = lambda: 20   # monster's saving throw
        Dice.roll = lambda size: 4
        monster = _monster()
        resolve_player_ability(self.char, self.abilities["fireball"], monster, [], 3)
        assert monster.hp == 100 - 12  # 6d6 (4 each) = 24, halved
        assert monster.effects == []

    def test_failed_save_takes_full_damage_and_burns(self):
        Dice.roll_d20 = lambda: 1
        Dice.roll = lambda size: 4
        monster = _monster()
        resolve_player_ability(self.char, self.abilities["fireball"], monster, [], 3)
        assert monster.hp == 100 - 24
        assert monster.effects[0]["stat"] == "burn"

    def test_save_uses_the_right_monster_modifier(self):
        Dice.roll_d20 = lambda: 5
        # DC = 8 + mod 3 + prof 1 = 12; WIS +7 turns a 5 into a successful save
        wise = _monster(wis_mod=7)
        resolve_player_ability(self.char, self.abilities["vicious_mockery"], wise, [], 3)
        assert wise.effects == []
        dull = _monster(wis_mod=0)
        resolve_player_ability(self.char, self.abilities["vicious_mockery"], dull, [], 3)
        assert dull.effects != []

    def test_bosses_resist_stun(self):
        Dice.roll_d20 = lambda: 15
        boss = _monster(boss_id="Shard Guardian")
        log = resolve_player_ability(self.char, self.abilities["stunning_strike"], boss, [], 3)
        assert boss.effects == []
        assert any("shrugs off" in line for line in log)

    def test_regular_monsters_can_be_stunned(self):
        Dice.roll_d20 = lambda: 15
        monster = _monster()
        resolve_player_ability(self.char, self.abilities["stunning_strike"], monster, [], 3)
        assert monster.effects[0]["stat"] == "stun"

    def test_self_buff_goes_to_player_effects(self):
        player_effects = []
        monster = _monster()
        resolve_player_ability(self.char, self.abilities["rallying_cry"], monster, player_effects, 3)
        assert player_effects[0]["stat"] == "damage_bonus"
        assert monster.effects == []

    def test_heal_caps_at_max_hp(self):
        Dice.roll = lambda size: size
        self.char.current_hit_points = self.char.max_hit_points - 1
        resolve_player_ability(self.char, self.abilities["second_wind"], _monster(), [], 3)
        assert self.char.current_hit_points == self.char.max_hit_points

    def test_every_ability_resolves_without_error(self):
        """Smoke test: all 60 abilities run against a monster at high level."""
        self.char.level = 12
        for ability in self.abilities.values():
            self.char.power_points = 10
            assert resolve_player_ability(self.char, ability, _monster(), [], 3) is not None
