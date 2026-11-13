"""Tests for campaign progression: bosses, shards, act unlocking."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import campaign as rules
from engine.combatant import CombatantState

ROOT = Path(__file__).parent.parent
CAMPAIGN = json.loads((ROOT / "json" / "campaign.json").read_text(encoding="utf-8"))
BOSSES = json.loads((ROOT / "json" / "bosses.json").read_text(encoding="utf-8"))
ABILITIES = json.loads((ROOT / "json" / "monster_abilities.json").read_text(encoding="utf-8"))["abilities"]

ACT1, ACT2, ACT3 = CAMPAIGN["acts"]
ACT1_BOSSES = rules.act_boss_ids(ACT1)
ACT2_BOSSES = rules.act_boss_ids(ACT2)
ACT3_BOSSES = rules.act_boss_ids(ACT3)


class TestData:
    def test_every_area_boss_is_defined(self):
        for act in CAMPAIGN["acts"]:
            for boss_id in rules.act_boss_ids(act):
                assert boss_id in BOSSES, f"Area boss '{boss_id}' missing from bosses.json"

    def test_bosses_are_well_formed(self):
        for boss_id, boss in BOSSES.items():
            for key in ("name", "level", "hp", "ac", "scores", "weapon", "abilities", "intro",
                        "defeat_text", "rewards", "taunts"):
                assert key in boss, f"{boss_id} missing {key}"
            for ability_id in boss["abilities"]:
                assert ability_id in ABILITIES, f"{boss_id} uses unknown ability {ability_id}"
            for requirement in boss.get("requires", []):
                assert requirement in BOSSES

    def test_five_crown_shards(self):
        assert len(rules.all_shards(BOSSES)) == 5

    def test_boss_combatant_state(self):
        state = CombatantState.from_boss("Shard Guardian", BOSSES["Shard Guardian"])
        assert state.is_boss
        assert state.hp == state.max_hp == BOSSES["Shard Guardian"]["hp"]
        assert state.ac == BOSSES["Shard Guardian"]["ac"]
        state.ac += 2
        state.reset_ac()
        assert state.ac == BOSSES["Shard Guardian"]["ac"], "reset_ac must restore the authored AC"
        assert CombatantState.from_dict(state.to_dict()) == state


class TestActProgression:
    def test_starts_in_act_one(self):
        assert rules.highest_unlocked_act(CAMPAIGN, []) == 1

    def test_partial_act_does_not_unlock_next(self):
        assert rules.highest_unlocked_act(CAMPAIGN, ACT1_BOSSES[:1]) == 1
        assert not rules.is_act_complete(ACT1, ACT1_BOSSES[:1])

    def test_completing_act_unlocks_next(self):
        assert rules.highest_unlocked_act(CAMPAIGN, ACT1_BOSSES) == 2
        assert rules.highest_unlocked_act(CAMPAIGN, ACT1_BOSSES + ACT2_BOSSES) == 3

    def test_acts_unlock_in_order(self):
        # Act 2 bosses alone don't skip past an unfinished Act 1
        assert rules.highest_unlocked_act(CAMPAIGN, ACT2_BOSSES) == 1

    def test_unlocked_act_never_exceeds_last_act(self):
        everything = ACT1_BOSSES + ACT2_BOSSES + ACT3_BOSSES
        assert rules.highest_unlocked_act(CAMPAIGN, everything) == 3
        assert rules.is_campaign_complete(CAMPAIGN, everything)

    def test_campaign_incomplete_until_final_boss(self):
        assert not rules.is_campaign_complete(CAMPAIGN, ACT1_BOSSES + ACT2_BOSSES + ACT3_BOSSES[:1])

    def test_ambush_boss_is_not_required_for_act_completion(self):
        assert "Lady Vex" not in ACT2_BOSSES


class TestBossesAndShards:
    def test_area_boss_lookup(self):
        grove = next(a for loc in ACT1["locations"] for a in loc["areas"] if a["id"] == "grove")
        assert rules.get_area_boss(grove, BOSSES, []) == "Shard Guardian"
        assert rules.get_area_boss(grove, BOSSES, ["Shard Guardian"]) is None
        assert rules.get_area_boss({"id": "x"}, BOSSES, []) is None
        assert rules.get_area_boss(None, BOSSES, []) is None

    def test_final_boss_requires_lieutenant(self):
        malachar = BOSSES["Malachar the Void-touched"]
        assert rules.missing_requirements(malachar, []) == ["Lady Vex (Final Battle)"]
        assert rules.missing_requirements(malachar, ["Lady Vex (Final Battle)"]) == []

    def test_shards_are_collected_from_shard_bosses_only(self):
        assert rules.collected_shards(BOSSES, []) == []
        assert rules.collected_shards(BOSSES, ["Corrupted Captain"]) == []
        assert rules.collected_shards(BOSSES, ["Shard Guardian"]) == ["Shard of Verdance"]

    def test_ambush_triggers_after_enough_act_bosses(self):
        assert rules.pending_ambush(BOSSES, ACT2, ACT1_BOSSES) is None
        assert rules.pending_ambush(BOSSES, ACT2, ACT1_BOSSES + ACT2_BOSSES[:1]) is None
        assert rules.pending_ambush(BOSSES, ACT2, ACT1_BOSSES + ACT2_BOSSES[:2]) == "Lady Vex"

    def test_ambush_only_in_its_own_act_and_only_once(self):
        defeated = ACT1_BOSSES + ACT2_BOSSES[:2]
        assert rules.pending_ambush(BOSSES, ACT1, defeated) is None
        assert rules.pending_ambush(BOSSES, ACT2, defeated + ["Lady Vex"]) is None
        assert rules.pending_ambush(BOSSES, None, defeated) is None
