"""Balance simulator — plays fights through the real routes with a sensible policy.

Usage (from the repo root, needs httpx installed):

    python tools/balance_sim.py bosses                 # every boss, at-level, 3 potions
    python tools/balance_sim.py bosses --level-delta 2 # over-levelled by 2
    python tools/balance_sim.py monsters               # a regular fight in each location
    python tools/balance_sim.py bosses --classes Monk,Druid --trials 40
    python tools/balance_sim.py bosses --classes all   # class comparison

Each cell shows win rate and average fight length in rounds. The simulated
player starts at full HP/PP with its ability score improvements spent on the
class's primary ability, heals below 45% HP (potion first, then a heal
ability), opens with a whole-combat self-buff if it has one, and otherwise uses
its highest expected-damage ability.

Targets used when the game was tuned: every class averaging roughly 60-80%
against at-level bosses with 3 potions, regular fights 90%+ with 1 potion.
One-round defensive abilities are never used, so classes that rely on them
score a little lower here than they play.
"""

import argparse
import json
import statistics
import sys
import tempfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402

import web.game_session as gs  # noqa: E402
from engine.leveling import ABILITY_SCORE_CAP, asi_points_earned  # noqa: E402
from web.app import app  # noqa: E402
from web.routes.battle import begin_boss_battle  # noqa: E402

BOSSES = gs.get_bosses()
ABILITIES = gs.get_abilities()
CLASSES = gs.get_classes()

# Starting weapon / armor per class
KIT = {
    "Fighter": ("Longsword", "Chain Mail"), "Wizard": ("Quarterstaff", ""),
    "Rogue": ("Rapier", "Leather"), "Cleric": ("Mace", "Chain Mail"),
    "Barbarian": ("Greataxe", "Hide"), "Ranger": ("Longbow", "Leather"),
    "Paladin": ("Longsword", "Chain Mail"), "Monk": ("Quarterstaff", ""),
    "Bard": ("Rapier", "Leather"), "Sorcerer": ("Dagger", ""),
    "Warlock": ("Dagger", "Leather"), "Druid": ("Quarterstaff", "Leather"),
}


def _boss_areas():
    areas = {}
    for act in gs.get_campaign()["acts"]:
        for location in act["locations"]:
            for area in location["areas"]:
                if area.get("boss"):
                    areas[area["boss"]] = (act["number"], location["name"], area["id"])
    return areas


def _monster_cases():
    """One mid-danger area per location that has monsters, with a typical player level."""
    cases = []
    for act in gs.get_campaign()["acts"]:
        for location in act["locations"]:
            areas = [a for a in location["areas"] if a.get("monster_types")]
            if not areas:
                continue
            area = sorted(areas, key=lambda a: a.get("encounters", 0))[len(areas) // 2]
            low, _, high = str(location.get("encounterLevel", "1-1")).partition("-")
            level = (int(low) + int(high or low)) // 2
            cases.append(((act["number"], location["name"], area["id"]), level))
    return cases


def _potion_for(level):
    if level <= 3:
        return "Small Healing Potion", 10
    if level <= 7:
        return "Healing Potion", 20
    if level <= 11:
        return "Greater Healing Potion", 35
    return "Superior Healing Potion", 50


def _expected_damage(ability, level):
    dmg = ability.get("damage")
    if not dmg or ability["target"] != "enemy":
        return 0
    dice = dmg["dice_count"]
    for threshold in sorted(ability.get("scaling", {}), key=int, reverse=True):
        if level >= int(threshold):
            dice = ability["scaling"][threshold].get("dice_count", dice)
            break
    bonus = 4 if dmg.get("bonus") == "ability_modifier" else level if dmg.get("bonus") == "level" else 0
    hit = {"auto_hit": 1.0, "spell_save": 0.75}.get(ability["attack_method"], 0.55)
    dot = sum(e["value"] * e["duration"] for e in ability.get("effects", [])
              if e["stat"] in ("poison", "burn", "bleed"))
    return (dice * (dmg["dice_size"] + 1) / 2 + bonus) * hit + dot


def run_fight(class_name, target, level, potions, sessions_dir):
    """Play one fight. `target` is a boss id or an (act, location, area_id) tuple.

    Returns (won, rounds, remaining_hp_fraction).
    """
    gs.SESSIONS_DIR = Path(sessions_dir)
    for stale in gs.SESSIONS_DIR.glob("*.json"):
        stale.unlink()

    with TestClient(app) as client:
        client.post("/character/race", data={"race": "Human"})
        client.post("/character/class", data={"class_name": class_name})
        weapon, armor = KIT[class_name]
        client.post("/character/create", data={"name": "Sim", "weapon": weapon, "armor": armor})

        path = next(gs.SESSIONS_DIR.glob("*.json"))
        data = json.loads(path.read_text())
        char = data["character"]
        hit_die = CLASSES[class_name]["hit_die"]
        char["level"] = level
        # Spend ability score improvements: primary ability first, then Constitution
        primary = CLASSES[class_name]["primary_ability"].lower()
        scores = {a: char[f"{a}_score"] for a in (primary, "constitution")}
        increases = {}
        for _ in range(asi_points_earned(level)):
            ability = primary if scores[primary] < ABILITY_SCORE_CAP else "constitution"
            scores[ability] += 1
            increases[ability] = increases.get(ability, 0) + 1
        char["ability_increases"] = increases
        con = (scores["constitution"] - 10) // 2
        char["max_hit_points"] = char["current_hit_points"] = (
            hit_die + con + (level - 1) * max(1, hit_die // 2 + 1 + con))
        char.pop("power_points", None)   # restored at max for the level
        name, healing = _potion_for(level)
        char["inventory"] = [{"name": name, "description": "", "type": "potion",
                              "healing_amount": healing}] * potions

        boss_areas = _boss_areas()
        if isinstance(target, tuple):
            data["act_num"], data["location_name"], data["area_id"] = target
            path.write_text(json.dumps(data))
            client.get("/battle/start")
        elif target in boss_areas:
            data["act_num"], data["location_name"], data["area_id"] = boss_areas[target]
            data["defeated_bosses"] = BOSSES[target].get("requires", [])
            path.write_text(json.dumps(data))
            client.post("/battle/boss")
        else:   # ambush boss: no area, start it directly
            session = gs.GameSession.from_dict(data)
            begin_boss_battle(session, target)
            path.write_text(json.dumps(session.to_dict()))

        known = [(aid, a) for aid, a in ABILITIES.items()
                 if class_name in a["classes"] and level >= a["unlock_level"]]

        for rounds in range(200):
            data = json.loads(path.read_text())
            char = data["character"]
            hp_fraction = char["current_hit_points"] / char["max_hit_points"]
            if not data["battle"]["is_active"]:
                return char["current_hit_points"] > 0, rounds, hp_fraction

            pp = char["power_points"]
            heals = [aid for aid, a in known if a.get("heal") and a["cost"] <= pp]
            if hp_fraction < 0.45 and char["inventory"]:
                client.post("/battle/item", data={"item_index": 0})
                continue
            if hp_fraction < 0.45 and heals:
                client.post("/battle/ability", data={"ability_id": heals[-1]})
                continue

            active_sources = {e["source"] for e in data["battle"]["player_effects"]}
            buffs = [aid for aid, a in known
                     if a["target"] == "self" and not a.get("heal") and a["cost"] <= pp
                     and any(e["duration"] == 0 for e in a.get("effects", []))
                     and a["name"] not in active_sources]
            if buffs and rounds < 3:
                client.post("/battle/ability", data={"ability_id": buffs[0]})
                continue

            attacks = [(_expected_damage(a, level), aid) for aid, a in known
                       if a["cost"] <= pp and _expected_damage(a, level) > 0]
            if attacks:
                client.post("/battle/ability", data={"ability_id": max(attacks)[1]})
            else:
                client.post("/battle/attack")
    return False, 200, 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("mode", choices=["bosses", "monsters"])
    parser.add_argument("--classes", default="Fighter,Wizard,Rogue,Cleric")
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--potions", type=int, default=None, help="default: 3 for bosses, 1 for monsters")
    parser.add_argument("--level-delta", type=int, default=0, help="player levels above the target")
    parser.add_argument("--only", default="", help="comma-separated boss ids or location names")
    args = parser.parse_args()

    classes = list(KIT) if args.classes == "all" else args.classes.split(",")
    only = [x for x in args.only.split(",") if x]
    if args.mode == "bosses":
        potions = 3 if args.potions is None else args.potions
        cases = [(boss_id, boss_id, boss["level"]) for boss_id, boss in BOSSES.items()]
    else:
        potions = 1 if args.potions is None else args.potions
        cases = [(where[1], where, level) for where, level in _monster_cases()]
    if only:
        cases = [c for c in cases if c[0] in only]

    with tempfile.TemporaryDirectory() as sessions_dir:
        for label, target, level in cases:
            level = max(1, level + args.level_delta)
            cells = []
            for class_name in classes:
                results = [run_fight(class_name, target, level, potions, sessions_dir)
                           for _ in range(args.trials)]
                wins = sum(r[0] for r in results) / args.trials
                rounds = statistics.mean(r[1] for r in results)
                hp = statistics.mean(r[2] for r in results)
                cells.append(f"{class_name[:5]:5s} {wins:4.0%} {rounds:4.1f}rd hp{hp:4.0%}")
            print(f"{label[:26]:26s} L{level:<2d} | " + " | ".join(cells), flush=True)


if __name__ == "__main__":
    main()
