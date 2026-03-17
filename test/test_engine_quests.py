"""Tests for engine.quests — quest progress, turn-in, and edge cases."""

import sys
import random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.quests import check_quest_progress, turn_in_quest
from items import QuestItem
from characterFactory import CharacterFactory


KILL_QUEST = {
    "name": "Goblin Menace",
    "type": "kill",
    "target_monster": "Goblin",
    "target_count": 3,
    "act": 1,
    "rewards": {"gold": 50, "xp": 200},
    "description": "Kill 3 goblins",
}

GATHER_QUEST = {
    "name": "Troll Tusks",
    "type": "gather",
    "target_monster": "Troll",
    "target_count": 2,
    "act": 1,
    "rewards": {"gold": 100, "xp": 300},
    "description": "Collect 2 troll tusks",
    "quest_item": {
        "name": "Troll Tusk",
        "description": "A gnarly tusk",
        "drop_chance": 1.0,  # guaranteed for testing
    },
}


class TestCheckQuestProgress:
    def test_kill_quest_increments(self):
        active = {"q1": {"progress": 0, "status": "active"}}
        all_quests = {"q1": KILL_QUEST}
        updates = check_quest_progress(active, all_quests, "Goblin", [])
        assert active["q1"]["progress"] == 1
        assert len(updates) == 1
        assert "1/3" in updates[0]

    def test_kill_quest_wrong_monster(self):
        active = {"q1": {"progress": 0, "status": "active"}}
        all_quests = {"q1": KILL_QUEST}
        updates = check_quest_progress(active, all_quests, "Orc", [])
        assert active["q1"]["progress"] == 0
        assert len(updates) == 0

    def test_kill_quest_completion(self):
        active = {"q1": {"progress": 2, "status": "active"}}
        all_quests = {"q1": KILL_QUEST}
        check_quest_progress(active, all_quests, "Goblin", [])
        assert active["q1"]["progress"] == 3
        assert active["q1"]["status"] == "ready"

    def test_ready_quest_not_updated(self):
        active = {"q1": {"progress": 3, "status": "ready"}}
        all_quests = {"q1": KILL_QUEST}
        updates = check_quest_progress(active, all_quests, "Goblin", [])
        assert active["q1"]["progress"] == 3  # unchanged
        assert len(updates) == 0

    def test_gather_quest_drops_item(self):
        active = {"q1": {"progress": 0, "status": "active"}}
        all_quests = {"q1": GATHER_QUEST}
        inventory = []
        updates = check_quest_progress(active, all_quests, "Troll", inventory)
        assert len(inventory) == 1
        assert isinstance(inventory[0], QuestItem)
        assert inventory[0].quest_id == "q1"
        assert active["q1"]["progress"] == 1
        assert "found" in updates[0]

    def test_gather_quest_no_drop(self):
        """With 0% drop chance, nothing drops."""
        no_drop_quest = {**GATHER_QUEST, "quest_item": {**GATHER_QUEST["quest_item"], "drop_chance": 0.0}}
        active = {"q1": {"progress": 0, "status": "active"}}
        all_quests = {"q1": no_drop_quest}
        inventory = []
        updates = check_quest_progress(active, all_quests, "Troll", inventory)
        assert len(inventory) == 0
        assert active["q1"]["progress"] == 0
        assert "no" in updates[0].lower()

    def test_gather_quest_completes(self):
        active = {"q1": {"progress": 1, "status": "active"}}
        all_quests = {"q1": GATHER_QUEST}
        # Pre-existing quest item in inventory
        inventory = [QuestItem("Troll Tusk", "A gnarly tusk", "q1")]
        check_quest_progress(active, all_quests, "Troll", inventory)
        # Now 2 items (1 existing + 1 dropped), target_count=2
        assert active["q1"]["status"] == "ready"

    def test_multiple_quests_tracked(self):
        active = {
            "q1": {"progress": 0, "status": "active"},
            "q2": {"progress": 0, "status": "active"},
        }
        quest2 = {**KILL_QUEST, "name": "More Goblins", "target_count": 5}
        all_quests = {"q1": KILL_QUEST, "q2": quest2}
        updates = check_quest_progress(active, all_quests, "Goblin", [])
        assert active["q1"]["progress"] == 1
        assert active["q2"]["progress"] == 1
        assert len(updates) == 2


class TestTurnInQuest:
    def _make_character(self):
        factory = CharacterFactory()
        char = factory.create_character("Hero", "Human", "Fighter")
        char.gold = 100
        char.xp = 0
        return char

    def test_successful_turn_in(self):
        char = self._make_character()
        active = {"q1": {"progress": 3, "status": "ready"}}
        completed = []
        all_quests = {"q1": KILL_QUEST}
        result = turn_in_quest("q1", active, completed, all_quests, char)
        assert result is not None
        assert result["gold"] == 50
        assert result["xp"] == 200
        assert result["quest_name"] == "Goblin Menace"
        assert char.gold == 150
        assert "q1" not in active
        assert "q1" in completed

    def test_not_ready_returns_none(self):
        char = self._make_character()
        active = {"q1": {"progress": 1, "status": "active"}}
        result = turn_in_quest("q1", active, [], {"q1": KILL_QUEST}, char)
        assert result is None
        assert "q1" in active  # not removed

    def test_nonexistent_quest_returns_none(self):
        char = self._make_character()
        result = turn_in_quest("bogus", {}, [], {}, char)
        assert result is None

    def test_gather_turn_in_removes_quest_items(self):
        char = self._make_character()
        char.inventory = [
            QuestItem("Troll Tusk", "tusk", "q1"),
            QuestItem("Troll Tusk", "tusk", "q1"),
            QuestItem("Other Item", "other", "q2"),  # different quest, should stay
        ]
        active = {"q1": {"progress": 2, "status": "ready"}}
        completed = []
        result = turn_in_quest("q1", active, completed, {"q1": GATHER_QUEST}, char)
        assert result is not None
        # Only the q2 item should remain
        assert len(char.inventory) == 1
        assert char.inventory[0].quest_id == "q2"

    def test_turn_in_grants_xp_and_may_level(self):
        char = self._make_character()
        char.xp = 140  # close to level 2 (need 150)
        active = {"q1": {"progress": 3, "status": "ready"}}
        result = turn_in_quest("q1", active, [], {"q1": KILL_QUEST}, char)
        assert result is not None
        assert len(result["level_ups"]) >= 1
        assert char.level >= 2
