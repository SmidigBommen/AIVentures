"""Core combat resolution — used by both web and CLI."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from engine.effects import get_effect_bonus, tick_effects


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
                        damage (int or 0 if miss)
    """
    attacker_effects = attacker_effects or []
    target_effects = target_effects or []

    atk_bonus = get_effect_bonus(attacker_effects, "attack_bonus")
    effective_ac = target_ac + get_effect_bonus(target_effects, "ac")

    roll = attack_roll(attacker_mod, attacker_prof, atk_bonus)
    hit = roll >= effective_ac

    damage = 0
    if hit:
        dmg_bonus = get_effect_bonus(attacker_effects, "damage_bonus")
        damage = roll_damage(damage_dice_count, damage_die, attacker_mod, dmg_bonus)
        dr = get_effect_bonus(target_effects, "damage_reduction")
        damage = max(1, damage - dr)

    return {
        "hit": hit,
        "attack_roll": roll,
        "target_ac": effective_ac,
        "damage": damage,
    }


def monster_turn_action():
    """Decide monster action: 'attack' (70%) or 'defend' (30%)."""
    return "attack" if random.random() < 0.7 else "defend"


def calculate_xp_reward(monster_level, round_count):
    """Calculate XP reward for defeating a monster."""
    base_xp = 100 * monster_level
    round_bonus = max(0, 10 * (10 - round_count))
    return base_xp + round_bonus


def calculate_gold_reward(monster_level):
    """Calculate gold reward for defeating a monster."""
    return monster_level * 5 + Dice.roll_d8()
