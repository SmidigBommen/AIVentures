"""Quest progress tracking and resolution."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from items import QuestItem


def check_quest_progress(active_quests, all_quests, monster_race, inventory):
    """Check and update quest progress after a monster kill.

    Args:
        active_quests: dict of {quest_id: {"progress": int, "status": str}}
        all_quests: dict of all quest definitions
        monster_race: race of the killed monster
        inventory: character's inventory list (items may be appended for gather quests)

    Returns:
        list of update message strings
    """
    updates = []

    for quest_id, quest_state in list(active_quests.items()):
        if quest_state["status"] != "active":
            continue
        quest_def = all_quests.get(quest_id)
        if not quest_def or quest_def["target_monster"] != monster_race:
            continue

        if quest_def["type"] == "kill":
            quest_state["progress"] = quest_state.get("progress", 0) + 1
            updates.append(f"{quest_def['name']}: {quest_state['progress']}/{quest_def['target_count']}")

        elif quest_def["type"] == "gather":
            qi = quest_def.get("quest_item", {})
            if random.random() < qi.get("drop_chance", 0.5):
                item = QuestItem(qi["name"], qi.get("description", ""), quest_id)
                inventory.append(item)
                count = sum(1 for it in inventory if isinstance(it, QuestItem) and it.quest_id == quest_id)
                quest_state["progress"] = count
                updates.append(f"{quest_def['name']}: found {qi['name']}! ({count}/{quest_def['target_count']})")
            else:
                updates.append(f"{quest_def['name']}: no {qi['name']} dropped this time")

        if quest_state["progress"] >= quest_def["target_count"]:
            quest_state["status"] = "ready"

    return updates


def turn_in_quest(quest_id, active_quests, completed_quests, all_quests, character):
    """Turn in a completed quest. Returns reward dict or None if not ready.

    Args:
        quest_id: ID of the quest to turn in
        active_quests: dict of active quests (will be modified)
        completed_quests: list of completed quest IDs (will be modified)
        all_quests: dict of all quest definitions
        character: the player character (gold/xp/inventory modified)

    Returns:
        dict with keys: gold, xp, quest_name, level_ups — or None if invalid
    """
    quest_def = all_quests.get(quest_id)
    quest_state = active_quests.get(quest_id)

    if not quest_def or not quest_state or quest_state["status"] != "ready":
        return None

    rewards = quest_def["rewards"]
    character.gold += rewards.get("gold", 0)
    level_ups = character.gain_xp(rewards.get("xp", 0))

    # Remove gather quest items from inventory
    if quest_def["type"] == "gather":
        character.inventory = [
            item for item in character.inventory
            if not (isinstance(item, QuestItem) and item.quest_id == quest_id)
        ]

    del active_quests[quest_id]
    completed_quests.append(quest_id)

    return {
        "gold": rewards.get("gold", 0),
        "xp": rewards.get("xp", 0),
        "quest_name": quest_def["name"],
        "level_ups": level_ups,
    }
