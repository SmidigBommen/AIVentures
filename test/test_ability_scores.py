"""Tests for class ability bonuses, Unarmored Defense, Ability Score Improvements
and the ability-kit features added with them (self effects, heal scaling)."""

import sys
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from armorFactory import ArmorFactory
from characterFactory import CharacterFactory
from engine.abilities import resolve_player_ability
from engine.combatant import CombatantState
from engine.leveling import (
    ABILITY_SCORE_CAP, ASI_LEVELS, apply_ability_increases, asi_points_available,
    asi_points_earned, calculate_max_pp, improve_ability,
)
from web.game_session import get_abilities, get_classes


def make(race="Human", class_name="Fighter"):
    char = CharacterFactory().create_character("Hero", race, class_name)
    primary = get_classes()[class_name]["primary_ability"].lower()
    char.max_power_points = char.power_points = calculate_max_pp(
        class_name, char.level, getattr(char, f"{primary}_modifier"))
    return char


class TestClassAbilityBonuses:
    def test_every_class_trains_its_primary_ability(self):
        for class_name, props in get_classes().items():
            bonuses = props["ability_bonuses"]
            assert bonuses[props["primary_ability"]] == 4, class_name
            assert sum(bonuses.values()) == 6, class_name

    def test_bonuses_stack_with_race(self):
        char = make("Half-orc", "Barbarian")
        assert char.strength_score == 10 + 2 + 4
        assert char.strength_modifier == 3
        assert char.constitution_score == 10 + 1 + 2

    def test_constitution_bonus_counts_toward_starting_hp(self):
        assert make("Human", "Fighter").max_hit_points == 10 + 1   # CON 13

    def test_modifiers_match_scores(self):
        for class_name in get_classes():
            char = make("Elf", class_name)
            for ability in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
                score = getattr(char, f"{ability}_score")
                assert getattr(char, f"{ability}_modifier") == (score - 10) // 2


class TestUnarmoredDefense:
    def test_monk_adds_wisdom_to_ac(self):
        monk = make("Human", "Monk")          # DEX 15 (+2), WIS 13 (+1)
        assert monk.armor_class == 10 + 2 + 1

    def test_armor_replaces_unarmored_defense(self):
        monk = make("Human", "Monk")
        monk.equip(ArmorFactory().get_armor_by_name("Leather"))
        assert monk.armor_class == 11 + 2

    def test_other_classes_get_plain_dexterity(self):
        wizard = make("Human", "Wizard")      # DEX 13 (+1)
        assert wizard.armor_class == 10 + 1


class TestAsiPoints:
    def test_points_by_level(self):
        assert asi_points_earned(1) == 0
        assert asi_points_earned(3) == 0
        assert asi_points_earned(4) == 2
        assert asi_points_earned(8) == 4
        assert asi_points_earned(20) == 2 * len(ASI_LEVELS)

    def test_available_subtracts_spent(self):
        char = make()
        char.level = 8
        assert asi_points_available(char) == 4
        char.ability_increases = {"strength": 3}
        assert asi_points_available(char) == 1


class TestImproveAbility:
    def test_needs_points(self):
        char = make()
        assert improve_ability(char, "strength", "Strength") is None
        assert char.strength_score == 15

    def test_spends_one_point_and_raises_score(self):
        char = make()
        char.level = 4
        result = improve_ability(char, "strength", "Strength")
        assert result["new_score"] == 16 and result["new_modifier"] == 3
        assert result["modifier_increased"] is True
        assert result["points_left"] == 1
        assert char.ability_increases == {"strength": 1}

    def test_unknown_ability_rejected(self):
        char = make()
        char.level = 4
        assert improve_ability(char, "luck", "Strength") is None
        assert asi_points_available(char) == 2

    def test_cap_at_twenty(self):
        char = make()
        char.level = 4
        char.strength_score = ABILITY_SCORE_CAP
        assert improve_ability(char, "strength", "Strength") is None
        assert asi_points_available(char) == 2

    def test_constitution_grants_hp_for_every_level(self):
        char = make()                 # CON 13 (+1)
        char.level = 4
        char.max_hit_points = 40
        char.current_hit_points = 25
        result = improve_ability(char, "constitution", "Strength")   # 14 -> +2
        assert result["hp_increase"] == 4
        assert char.max_hit_points == 44 and char.current_hit_points == 29

    def test_constitution_without_modifier_change_gives_no_hp(self):
        char = make()
        char.level = 4
        improve_ability(char, "constitution", "Strength")            # 14
        result = improve_ability(char, "constitution", "Strength")   # 15, still +2
        assert result["hp_increase"] == 0

    def test_primary_ability_grows_power_points(self):
        wizard = make("Human", "Wizard")       # INT 15 (+2)
        wizard.level = 4
        wizard.max_power_points = calculate_max_pp("Wizard", 4, 2)
        wizard.power_points = 1
        result = improve_ability(wizard, "intelligence", "Intelligence")   # 16 -> +3
        assert result["pp_increase"] == 1
        assert wizard.max_power_points == 7 and wizard.power_points == 2

    def test_dexterity_updates_ac(self):
        rogue = make("Human", "Rogue")         # DEX 15 (+2)
        rogue.level = 4
        before = rogue.armor_class
        improve_ability(rogue, "dexterity", "Dexterity")
        assert rogue.armor_class == before + 1

    def test_apply_ability_increases_rebuilds_scores(self):
        char = make()
        apply_ability_increases(char, {"strength": 3, "bogus": 2, "wisdom": 0})
        assert char.strength_score == 18 and char.strength_modifier == 4
        assert char.ability_increases == {"strength": 3}


class TestAbilityKitFeatures:
    def setup_method(self):
        self._orig_d20, self._orig_roll = Dice.roll_d20, Dice.roll
        self.abilities = get_abilities()
        self.monster = CombatantState(name="Grak", race="Orc", level=3, hp=500, max_hp=500,
                                      ac=12, base_ac=11)

    def teardown_method(self):
        Dice.roll_d20, Dice.roll = self._orig_d20, self._orig_roll

    def test_reckless_attack_lowers_own_ac_even_on_a_miss(self):
        barbarian = make("Human", "Barbarian")
        Dice.roll_d20 = lambda: 2
        effects = []
        resolve_player_ability(barbarian, self.abilities["reckless_attack"], self.monster, effects, 3)
        assert self.monster.hp == 500
        assert [(e["stat"], e["value"], e["duration"]) for e in effects] == [("ac", -3, 1)]

    def test_heal_scales_with_level(self):
        cleric = make("Human", "Cleric")
        cleric.max_hit_points, cleric.power_points = 500, 10
        Dice.roll = lambda sides: 1
        healed = {}
        for level in (1, 9):
            cleric.level, cleric.current_hit_points = level, 1
            resolve_player_ability(cleric, self.abilities["cure_wounds"], self.monster, [], 0)
            healed[level] = cleric.current_hit_points - 1
        assert healed == {1: 1, 9: 3}

    def test_damage_scaling_does_not_scale_the_heal_of_a_damage_ability(self):
        paladin = make("Human", "Paladin")
        paladin.level, paladin.power_points = 13, 10
        paladin.max_hit_points, paladin.current_hit_points = 500, 1
        Dice.roll_d20, Dice.roll = (lambda: 15), (lambda sides: 1)
        resolve_player_ability(paladin, self.abilities["holy_smite"], self.monster, [], 0)
        assert paladin.current_hit_points == 2          # 1d6 heal, not scaled
        assert self.monster.hp == 500 - 6               # 6 dice at level 13

    def test_every_damage_ability_keeps_growing_or_is_free(self):
        """Paid damage abilities must scale, or free ones overtake them at high level."""
        for ability_id, ability in self.abilities.items():
            if ability.get("damage") and ability["cost"] >= 2:
                assert ability.get("scaling"), ability_id

    def test_monk_has_a_ki_sized_power_pool(self):
        assert calculate_max_pp("Monk", 10, 3) == 8
        assert calculate_max_pp("Fighter", 10, 3) == 6


# --- Through the routes ----------------------------------------------------

pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

import web.game_session as game_session  # noqa: E402
from web.app import app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(game_session, "SESSIONS_DIR", tmp_path)
    with TestClient(app) as c:
        c.post("/character/race", data={"race": "Human"})
        c.post("/character/class", data={"class_name": "Rogue"})
        c.post("/character/create", data={
            "name": "Tester", "weapon": "Rapier", "armor": "Leather",
            "skills": ["Stealth", "Perception", "Acrobatics", "Deception"]})
        c.path = next(tmp_path.glob("*.json"))
        yield c


def _load(client):
    return json.loads(client.path.read_text(encoding="utf-8"))


def _set_level(client, level):
    data = _load(client)
    data["character"]["level"] = level
    client.path.write_text(json.dumps(data), encoding="utf-8")


class TestImproveRoute:
    def test_sheet_has_no_improve_buttons_without_points(self, client):
        page = client.get("/character/summary").text
        assert "/character/improve" not in page
        assert "nav-badge" not in page

    def test_sheet_offers_points_at_level_four(self, client):
        _set_level(client, 4)
        page = client.get("/character/summary").text
        assert "2 points to spend" in page
        assert page.count('action="/character/improve"') == 6
        assert "nav-badge" in page

    def test_spending_points_persists_and_updates_ac(self, client):
        _set_level(client, 4)
        before = _load(client)["character"]
        assert (before["dexterity_score"], before["armor_class"]) == (15, 13)
        for _ in range(2):
            response = client.post("/character/improve", data={"ability": "dexterity"},
                                   follow_redirects=False)
            assert response.headers["location"] == "/character/summary"
        after = _load(client)["character"]
        assert after["dexterity_score"] == 17 and after["dexterity_modifier"] == 3
        assert after["armor_class"] == 14
        assert after["ability_increases"] == {"dexterity": 2}
        assert after["asi_points"] == 0
        page = client.get("/character/summary").text
        assert "Dexterity is now 17" in page
        assert "/character/improve" not in page

    def test_cannot_overspend(self, client):
        _set_level(client, 4)
        for _ in range(5):
            client.post("/character/improve", data={"ability": "strength"})
        assert _load(client)["character"]["ability_increases"] == {"strength": 2}

    def test_old_save_without_increases_gets_its_points(self, client):
        data = _load(client)
        data["character"]["level"] = 9
        data["character"].pop("ability_increases")
        data["character"]["armor_class"] = 99       # stale value from an old save
        client.path.write_text(json.dumps(data), encoding="utf-8")
        client.get("/character/summary")
        client.post("/character/improve", data={"ability": "constitution"})
        char = _load(client)["character"]
        assert char["asi_points"] == 3
        assert char["armor_class"] == 13

    def test_class_page_shows_training(self, client):
        assert "+4 DEX, +2 INT" in client.get("/character/class").text
