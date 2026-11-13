"""Exploration events — skill-check encounters found while exploring.

Events are data-driven (json/events.json):

    {
      "title": "...", "text": "...",
      "location_types": ["wilderness", "dungeon"],   # omit = anywhere
      "special": "hidden_treasure",                  # only in areas with this special
      "once": true,                                  # can be completed a single time
      "choices": [
        {"label": "Pick the lock", "skill": "Sleight of Hand", "dc": 12,
         "success": {"text": "...", "gold": 20, "xp": 15},
         "failure": {"text": "...", "damage": [1, 6]}},
        {"label": "Walk away", "outcome": {"text": "..."}}
      ]
    }

Outcome keys: text, gold (negative = loss), xp, heal_pct, pp, damage [count, size],
potion (bool), battle (bool — the outcome starts a fight).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from items import HealingPotion
from skills import make_skill_check

POTIONS_BY_TIER = (
    (3, "Small Healing Potion", 10),
    (7, "Healing Potion", 20),
    (11, "Greater Healing Potion", 35),
    (999, "Superior Healing Potion", 50),
)


def eligible_events(events, location_type, special, completed):
    """Split events available here into (special_events, general_events)."""
    special_ids, general_ids = [], []
    for event_id, event in events.items():
        if event.get("once") and event_id in completed:
            continue
        if event.get("special"):
            if special and event["special"] == special:
                special_ids.append(event_id)
            continue
        types = event.get("location_types")
        if types and location_type not in types:
            continue
        general_ids.append(event_id)
    return special_ids, general_ids


def pick_event(events, location_type, special, completed):
    """Choose an event for this area. Unfinished special-area events take priority."""
    special_ids, general_ids = eligible_events(events, location_type, special, completed)
    if special_ids:
        return random.choice(special_ids)
    if general_ids:
        return random.choice(general_ids)
    return None


def scaled_dc(dc, tier):
    """Checks get slightly harder in more dangerous lands."""
    return dc + tier // 5


def _potion_for_tier(tier):
    for max_level, name, healing in POTIONS_BY_TIER:
        if tier <= max_level:
            return HealingPotion(name, healing)


def apply_outcome(character, outcome, tier):
    """Apply an outcome to the character. XP is reported, not applied (caller handles leveling).

    Returns:
        dict with keys: text, gold, xp, heal, pp, damage, item, battle
    """
    result = {"text": outcome.get("text", ""), "gold": 0, "xp": 0, "heal": 0,
              "pp": 0, "damage": 0, "item": None, "battle": bool(outcome.get("battle"))}

    gold = outcome.get("gold", 0)
    if gold > 0:
        gold = round(gold * (1 + tier / 3))
        character.gold += gold
    elif gold < 0:
        gold = -min(character.gold, round(-gold * (1 + tier / 3)))
        character.gold += gold
    result["gold"] = gold

    if outcome.get("xp"):
        result["xp"] = outcome["xp"] * max(1, tier)

    if outcome.get("heal_pct"):
        amount = max(1, character.max_hit_points * outcome["heal_pct"] // 100)
        old = character.current_hit_points
        character.current_hit_points = min(character.max_hit_points, old + amount)
        result["heal"] = character.current_hit_points - old

    if outcome.get("pp"):
        old = character.power_points
        character.power_points = min(character.max_power_points, old + outcome["pp"])
        result["pp"] = character.power_points - old

    if outcome.get("damage"):
        count, size = outcome["damage"]
        damage = sum(Dice.roll(size) for _ in range(count + tier // 4))
        # Mishaps hurt, but an event never kills outright
        damage = min(damage, character.current_hit_points - 1)
        character.current_hit_points -= max(0, damage)
        result["damage"] = max(0, damage)

    if outcome.get("potion"):
        potion = _potion_for_tier(tier)
        character.add_item(potion)
        result["item"] = potion.name

    return result


def resolve_event_choice(character, event, choice_index, tier=1):
    """Resolve the player's choice for an event.

    Returns:
        result dict (see apply_outcome) plus: label, success (bool),
        check (skill check dict or None) — or None for an invalid choice.
    """
    choices = event.get("choices", [])
    if not 0 <= choice_index < len(choices):
        return None
    choice = choices[choice_index]

    check = None
    if choice.get("skill"):
        check = make_skill_check(character, choice["skill"], scaled_dc(choice.get("dc", 10), tier))
        # Natural 20 always succeeds, natural 1 always fails
        if check["roll"] == 20:
            check["success"] = True
        elif check["roll"] == 1:
            check["success"] = False
        outcome = choice["success"] if check["success"] else choice["failure"]
        success = check["success"]
    else:
        outcome = choice.get("outcome", {})
        success = True

    result = apply_outcome(character, outcome, tier)
    result.update({"label": choice["label"], "success": success, "check": check})
    return result
