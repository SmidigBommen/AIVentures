"""Core combat resolution — headless D&D-style attack, damage and reward rules."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from engine.effects import get_effect_bonus


def roll_initiative(dex_mod_a, dex_mod_b):
    """Roll initiative for two combatants. Returns (a_roll, b_roll)."""
    return dex_mod_a + Dice.roll_d20(), dex_mod_b + Dice.roll_d20()


def attack_roll(ability_mod, proficiency_bonus, effect_bonus=0):
    """Make an attack roll. Returns the total."""
    return Dice.roll_d20() + ability_mod + proficiency_bonus + effect_bonus


def roll_damage(dice_count, dice_size, ability_mod=0, bonus=0):
    """Roll damage dice + modifiers. Returns total (min 1)."""
    damage = sum(Dice.roll(dice_size) for _ in range(dice_count))
    return max(1, damage + ability_mod + bonus)


def get_weapon_attack_modifier(str_mod, dex_mod, weapon_properties):
    """Determine the correct ability modifier for a weapon based on properties."""
    if "ammunition" in weapon_properties:
        return dex_mod
    if "finesse" in weapon_properties:
        return max(str_mod, dex_mod)
    return str_mod


def resolve_attack_roll(attack_bonus, target_ac):
    """Roll a d20 attack against an AC using D&D 5e critical rules.

    A natural 20 always hits and is a critical hit; a natural 1 always misses.

    Returns:
        dict with keys: natural (int), total (int), hit (bool), crit (bool), fumble (bool)
    """
    natural = Dice.roll_d20()
    total = natural + attack_bonus
    crit = natural == 20
    fumble = natural == 1
    hit = crit or (not fumble and total >= target_ac)
    return {"natural": natural, "total": total, "hit": hit, "crit": crit, "fumble": fumble}


def resolve_weapon_attack(attacker_mod, attacker_prof, target_ac,
                          damage_dice_count, damage_die,
                          attacker_effects=None, target_effects=None):
    """Resolve a weapon attack. Returns a result dict.

    Args:
        attacker_mod: Ability modifier for the weapon.
        attacker_prof: Proficiency bonus.
        target_ac: Target's base armor class.
        damage_dice_count: Number of damage dice.
        damage_die: Size of damage die (e.g. 8 for d8).
        attacker_effects: List of active effects on attacker.
        target_effects: List of active effects on target.

    Returns:
        dict with keys: hit (bool), attack_roll (int), target_ac (int),
                        damage (int or 0 if miss), crit (bool), fumble (bool),
                        natural (int, the unmodified d20)
    """
    attacker_effects = attacker_effects or []
    target_effects = target_effects or []

    atk_bonus = get_effect_bonus(attacker_effects, "attack_bonus")
    effective_ac = target_ac + get_effect_bonus(target_effects, "ac")

    roll = resolve_attack_roll(attacker_mod + attacker_prof + atk_bonus, effective_ac)

    damage = 0
    if roll["hit"]:
        dmg_bonus = get_effect_bonus(attacker_effects, "damage_bonus")
        # Critical hits roll the damage dice twice (modifiers are not doubled)
        dice = damage_dice_count * 2 if roll["crit"] else damage_dice_count
        damage = roll_damage(dice, damage_die, attacker_mod, dmg_bonus)
        dr = get_effect_bonus(target_effects, "damage_reduction")
        damage = max(1, damage - dr)

    return {
        "hit": roll["hit"],
        "attack_roll": roll["total"],
        "target_ac": effective_ac,
        "damage": damage,
        "crit": roll["crit"],
        "fumble": roll["fumble"],
        "natural": roll["natural"],
    }


def resolve_flee(dex_mod, monster_level):
    """Attempt to flee combat: d20 + DEX vs DC 10 + monster_level // 2.

    Returns dict with keys: success (bool), roll (int), total (int), dc (int)
    """
    roll = Dice.roll_d20()
    dc = 10 + monster_level // 2
    total = roll + dex_mod
    success = roll == 20 or (roll != 1 and total >= dc)
    return {"success": success, "roll": roll, "total": total, "dc": dc}


def monster_turn_action():
    """Simple coin-flip AI: 'attack' (70%) or 'defend' (30%).

    Battles use engine.monster_ai.choose_monster_action(), which also handles
    special abilities; this remains as the minimal fallback.
    """
    return "attack" if random.random() < 0.7 else "defend"


def calculate_xp_reward(monster_level, round_count):
    """Calculate XP reward for defeating a monster."""
    base_xp = 100 * monster_level
    round_bonus = max(0, 10 * (10 - round_count))
    return base_xp + round_bonus


def roll_dice(dice_count, dice_size):
    """Roll NdS and return the sum."""
    return sum(Dice.roll(dice_size) for _ in range(dice_count))


def calculate_gold_reward(monster_level):
    """Calculate gold reward for defeating a monster."""
    return monster_level * 5 + Dice.roll_d8()
