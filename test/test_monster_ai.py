"""Tests for monster special abilities and action selection."""

import sys
import json
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from engine.combatant import CombatantState
from engine.monster_ai import (
    available_abilities, choose_monster_action, resolve_monster_ability, tick_cooldowns,
)

ROOT = Path(__file__).parent.parent
DATA = json.loads((ROOT / "json" / "monster_abilities.json").read_text(encoding="utf-8"))
CATALOG = DATA["abilities"]
SAVES = {a: 0 for a in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")}


def _monster(**kwargs):
    defaults = dict(name="Grak", race="Orc", level=4, hp=30, max_hp=30, ac=12, base_ac=11,
                    str_mod=3, dex_mod=1, con_mod=2, proficiency=2)
    defaults.update(kwargs)
    return CombatantState(**defaults)


class _FixedDice:
    """Pin d20 and damage dice for deterministic resolution."""

    def setup_method(self):
        self._orig_d20, self._orig_roll = Dice.roll_d20, Dice.roll

    def teardown_method(self):
        Dice.roll_d20, Dice.roll = self._orig_d20, self._orig_roll


class TestData:
    def test_every_race_ability_exists(self):
        for race, ids in DATA["races"].items():
            for ability_id in ids:
                assert ability_id in CATALOG, f"{race} references unknown ability {ability_id}"

    def test_every_monster_race_has_abilities(self):
        races = json.loads((ROOT / "json" / "monster_default_values.json").read_text(encoding="utf-8"))
        for race in races:
            assert DATA["races"].get(race), f"{race} has no special abilities"

    def test_abilities_are_well_formed(self):
        for ability_id, ability in CATALOG.items():
            assert ability["kind"] in ("attack", "save", "self"), ability_id
            assert ability.get("name") and ability.get("text"), ability_id
            if ability["kind"] == "save":
                assert ability.get("save_ability"), ability_id
            for effect in ability.get("effects", []):
                assert {"stat", "value", "duration", "target"} <= set(effect), ability_id
                assert effect["target"] in ("player", "self"), ability_id
                if ability["kind"] == "self":
                    assert effect["target"] == "self", ability_id


class TestAvailability:
    def test_cooldown_blocks_ability(self):
        m = _monster(abilities=["savage_cleave"], cooldowns={"savage_cleave": 2})
        assert available_abilities(m, CATALOG) == []
        tick_cooldowns(m)
        assert available_abilities(m, CATALOG) == []
        tick_cooldowns(m)
        assert available_abilities(m, CATALOG) == ["savage_cleave"]

    def test_heal_only_available_when_wounded(self):
        m = _monster(abilities=["regenerate"])
        assert available_abilities(m, CATALOG) == []
        m.hp = 10
        assert available_abilities(m, CATALOG) == ["regenerate"]

    def test_running_self_buff_is_not_recast(self):
        m = _monster(abilities=["war_cry"])
        assert available_abilities(m, CATALOG) == ["war_cry"]
        m.effects.append({"stat": "damage_bonus", "value": 2, "duration": 3, "source": "War Cry"})
        assert available_abilities(m, CATALOG) == []

    def test_unknown_ability_ids_are_ignored(self):
        m = _monster(abilities=["does_not_exist"])
        assert available_abilities(m, CATALOG) == []


class TestActionChoice:
    def test_no_abilities_means_attack_or_defend(self):
        random.seed(1)
        m = _monster()
        actions = {choose_monster_action(m, CATALOG)[0] for _ in range(200)}
        assert actions == {"attack", "defend"}

    def test_never_defends_when_player_is_nearly_dead(self):
        random.seed(2)
        m = _monster()
        actions = {choose_monster_action(m, CATALOG, player_hp_fraction=0.2)[0] for _ in range(200)}
        assert actions == {"attack"}

    def test_uses_abilities_sometimes(self):
        random.seed(3)
        m = _monster(abilities=["savage_cleave"])
        picks = [choose_monster_action(m, CATALOG) for _ in range(200)]
        assert ("ability", "savage_cleave") in picks
        assert any(action == "attack" for action, _ in picks)

    def test_wounded_monster_prefers_healing(self):
        random.seed(4)
        m = _monster(abilities=["regenerate"], hp=5)
        picks = [choose_monster_action(m, CATALOG) for _ in range(200)]
        assert picks.count(("ability", "regenerate")) > 100


class TestResolution(_FixedDice):
    def test_attack_ability_hit_deals_damage_and_applies_effect(self):
        Dice.roll_d20 = lambda: 15
        Dice.roll = lambda size: 3
        m = _monster(abilities=["savage_cleave"])
        player_effects = []
        result = resolve_monster_ability(m, "savage_cleave", CATALOG["savage_cleave"], 12, player_effects, SAVES)
        # 2d6 (3 each) + STR 3 = 9
        assert result["landed"] is True
        assert result["damage"] == 9
        assert player_effects[0]["stat"] == "bleed"

    def test_timed_effects_get_an_extra_round(self):
        """Monsters act last in the round, so durations are padded by one."""
        Dice.roll_d20 = lambda: 15
        Dice.roll = lambda size: 3
        m = _monster()
        player_effects = []
        resolve_monster_ability(m, "savage_cleave", CATALOG["savage_cleave"], 12, player_effects, SAVES)
        authored = CATALOG["savage_cleave"]["effects"][0]["duration"]
        assert player_effects[0]["duration"] == authored + 1

    def test_attack_ability_miss_does_nothing(self):
        Dice.roll_d20 = lambda: 2
        m = _monster()
        player_effects = []
        result = resolve_monster_ability(m, "savage_cleave", CATALOG["savage_cleave"], 18, player_effects, SAVES)
        assert result["landed"] is False
        assert result["damage"] == 0
        assert player_effects == []

    def test_successful_save_halves_damage_and_blocks_rider(self):
        Dice.roll_d20 = lambda: 19
        Dice.roll = lambda size: 4
        m = _monster(race="Fire Salamander")
        player_effects = []
        result = resolve_monster_ability(m, "fire_breath", CATALOG["fire_breath"], 12, player_effects, SAVES)
        # level 4: 2 + 4//4 = 3d6 (4 each) + CON 2 = 14, halved = 7
        assert result["damage"] == 7
        assert player_effects == []

    def test_failed_save_takes_full_damage_and_rider(self):
        Dice.roll_d20 = lambda: 2
        Dice.roll = lambda size: 4
        m = _monster(race="Fire Salamander")
        player_effects = []
        result = resolve_monster_ability(m, "fire_breath", CATALOG["fire_breath"], 12, player_effects, SAVES)
        assert result["damage"] == 14
        assert player_effects[0]["stat"] == "burn"

    def test_save_modifier_is_used(self):
        Dice.roll_d20 = lambda: 5
        m = _monster()  # DC = 8 + prof 2 + CON 2 = 12
        good_saves = dict(SAVES, dexterity=7)
        assert resolve_monster_ability(m, "fire_breath", CATALOG["fire_breath"], 12, [], good_saves)["landed"] is False
        assert resolve_monster_ability(m, "fire_breath", CATALOG["fire_breath"], 12, [], SAVES)["landed"] is True

    def test_damage_reduction_protects_player(self):
        Dice.roll_d20 = lambda: 15
        Dice.roll = lambda size: 3
        m = _monster()
        player_effects = [{"stat": "damage_reduction", "value": 5, "duration": 1, "source": "Evasion"}]
        result = resolve_monster_ability(m, "savage_cleave", CATALOG["savage_cleave"], 12, player_effects, SAVES)
        assert result["damage"] == 4

    def test_lifesteal_heals_monster(self):
        Dice.roll_d20 = lambda: 2
        Dice.roll = lambda size: 4
        m = _monster(hp=10, cha_mod=2)
        result = resolve_monster_ability(m, "life_drain", CATALOG["life_drain"], 12, [], SAVES)
        assert m.hp == 10 + result["damage"]

    def test_self_heal_caps_at_max_hp(self):
        Dice.roll = lambda size: size
        m = _monster(hp=28)
        resolve_monster_ability(m, "regenerate", CATALOG["regenerate"], 12, [], SAVES)
        assert m.hp == m.max_hp

    def test_self_buff_lands_on_monster(self):
        m = _monster()
        player_effects = []
        resolve_monster_ability(m, "war_cry", CATALOG["war_cry"], 12, player_effects, SAVES)
        assert m.effects[0]["stat"] == "damage_bonus"
        assert player_effects == []

    def test_cooldown_is_set(self):
        m = _monster()
        resolve_monster_ability(m, "war_cry", CATALOG["war_cry"], 12, [], SAVES)
        assert m.cooldowns["war_cry"] == CATALOG["war_cry"]["cooldown"] + 1
