"""Tests for exploration events (engine/events.py + json/events.json)."""

import sys
import json
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from skills import SKILLS
from items import HealingPotion
from characterFactory import CharacterFactory
from engine.events import (
    eligible_events, pick_event, resolve_event_choice, apply_outcome, scaled_dc,
)

ROOT = Path(__file__).parent.parent
EVENTS = json.loads((ROOT / "json" / "events.json").read_text(encoding="utf-8"))
CAMPAIGN = json.loads((ROOT / "json" / "campaign.json").read_text(encoding="utf-8"))
OUTCOME_KEYS = {"text", "gold", "xp", "heal_pct", "pp", "damage", "potion", "battle"}

CHEST = {
    "title": "Chest", "text": "A chest.",
    "choices": [
        {"label": "Pick", "skill": "Sleight of Hand", "dc": 12,
         "success": {"text": "Open!", "gold": 30, "xp": 10, "potion": True},
         "failure": {"text": "Ouch.", "damage": [1, 6]}},
        {"label": "Leave", "outcome": {"text": "You leave."}},
    ],
}


def _character():
    char = CharacterFactory().create_character("Hero", "Human", "Rogue")
    char.gold = 50
    char.power_points, char.max_power_points = 1, 5
    return char


class TestData:
    def test_events_are_well_formed(self):
        for event_id, event in EVENTS.items():
            assert event.get("title") and event.get("text"), event_id
            assert len(event["choices"]) >= 2, event_id
            for choice in event["choices"]:
                assert choice.get("label"), event_id
                if "skill" in choice:
                    assert choice["skill"] in SKILLS, f"{event_id}: unknown skill {choice['skill']}"
                    outcomes = [choice["success"], choice["failure"]]
                else:
                    outcomes = [choice["outcome"]]
                for outcome in outcomes:
                    assert outcome.get("text"), event_id
                    assert set(outcome) <= OUTCOME_KEYS, f"{event_id}: {set(outcome) - OUTCOME_KEYS}"

    def test_special_events_match_a_real_area(self):
        specials = {a.get("special") for act in CAMPAIGN["acts"]
                    for loc in act["locations"] for a in loc["areas"]}
        for event_id, event in EVENTS.items():
            if event.get("special"):
                assert event["special"] in specials, event_id
                assert event.get("once"), f"{event_id}: special events should be one-time"

    def test_every_location_type_has_general_events(self):
        for loc_type in ("town", "wilderness", "dungeon"):
            _, general = eligible_events(EVENTS, loc_type, None, [])
            assert len(general) >= 2, loc_type

    def test_battle_outcomes_only_where_monsters_live(self):
        """An event that starts a fight must not be able to fire somewhere with no monsters."""
        for event_id, event in EVENTS.items():
            has_battle = any(
                o.get("battle")
                for c in event["choices"]
                for o in (c.get("success"), c.get("failure"), c.get("outcome")) if o)
            if has_battle and not event.get("special"):
                assert "town" not in event.get("location_types", ["town"]), event_id


class TestSelection:
    def test_special_event_takes_priority(self):
        random.seed(0)
        for _ in range(20):
            assert pick_event(EVENTS, "dungeon", "hidden_treasure", []) == "cellar_cache"

    def test_completed_special_falls_back_to_general(self):
        random.seed(0)
        picked = pick_event(EVENTS, "dungeon", "hidden_treasure", ["cellar_cache"])
        assert picked != "cellar_cache"
        assert not EVENTS[picked].get("special")

    def test_location_type_filter(self):
        _, general = eligible_events(EVENTS, "town", None, [])
        for event_id in general:
            assert "town" in EVENTS[event_id].get("location_types", ["town"])

    def test_no_events_returns_none(self):
        assert pick_event({}, "town", None, []) is None


class TestResolution:
    def setup_method(self):
        self._orig_d20, self._orig_roll = Dice.roll_d20, Dice.roll

    def teardown_method(self):
        Dice.roll_d20, Dice.roll = self._orig_d20, self._orig_roll

    def test_success_grants_rewards(self):
        Dice.roll_d20 = lambda: 19
        char = _character()
        result = resolve_event_choice(char, CHEST, 0, tier=1)
        assert result["success"] is True
        assert result["gold"] == 40          # 30 * (1 + 1/3)
        assert char.gold == 90
        assert result["xp"] == 10            # reported for the caller to apply
        assert char.xp == 0
        assert any(isinstance(i, HealingPotion) for i in char.inventory)
        assert result["check"]["skill"] == "Sleight of Hand"

    def test_failure_deals_damage(self):
        Dice.roll_d20 = lambda: 2
        Dice.roll = lambda size: 3
        char = _character()
        hp = char.current_hit_points
        result = resolve_event_choice(char, CHEST, 0, tier=1)
        assert result["success"] is False
        assert result["damage"] == 3
        assert char.current_hit_points == hp - 3

    def test_event_damage_never_kills(self):
        Dice.roll_d20 = lambda: 2
        Dice.roll = lambda size: 100
        char = _character()
        resolve_event_choice(char, CHEST, 0, tier=1)
        assert char.current_hit_points == 1

    def test_natural_20_always_succeeds_and_natural_1_always_fails(self):
        char = _character()
        hard = {"choices": [{"label": "x", "skill": "Athletics", "dc": 99,
                             "success": {"text": "s"}, "failure": {"text": "f"}}]}
        easy = {"choices": [{"label": "x", "skill": "Athletics", "dc": -50,
                             "success": {"text": "s"}, "failure": {"text": "f"}}]}
        Dice.roll_d20 = lambda: 20
        assert resolve_event_choice(char, hard, 0)["success"] is True
        Dice.roll_d20 = lambda: 1
        assert resolve_event_choice(char, easy, 0)["success"] is False

    def test_no_check_choice(self):
        char = _character()
        result = resolve_event_choice(char, CHEST, 1)
        assert result["check"] is None
        assert result["text"] == "You leave."

    def test_invalid_choice_returns_none(self):
        assert resolve_event_choice(_character(), CHEST, 7) is None
        assert resolve_event_choice(_character(), CHEST, -1) is None

    def test_rewards_scale_with_tier(self):
        low, high = _character(), _character()
        r1 = apply_outcome(low, {"gold": 30, "xp": 10}, tier=1)
        r9 = apply_outcome(high, {"gold": 30, "xp": 10}, tier=9)
        assert r9["gold"] > r1["gold"]
        assert r9["xp"] == 90
        assert scaled_dc(12, 1) == 12 and scaled_dc(12, 13) == 14

    def test_gold_loss_cannot_go_negative(self):
        char = _character()
        char.gold = 3
        result = apply_outcome(char, {"gold": -50}, tier=1)
        assert char.gold == 0
        assert result["gold"] == -3

    def test_heal_and_pp_are_capped(self):
        char = _character()
        char.current_hit_points = char.max_hit_points - 1
        result = apply_outcome(char, {"heal_pct": 100, "pp": 99}, tier=1)
        assert result["heal"] == 1
        assert char.power_points == char.max_power_points
        assert result["pp"] == 4
