"""Player class ability resolution (data in json/abilities.json)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from engine.combat import resolve_attack_roll, roll_dice
from engine.effects import get_effect_bonus, describe_effect


def _bonus(data, primary_mod, level):
    bonus = data.get("bonus", 0)
    if bonus == "ability_modifier":
        return primary_mod
    if bonus == "level":
        return level
    return bonus if isinstance(bonus, int) else 0


def _scaled_dice_count(ability, base_count, level):
    """Level scaling: the highest threshold at or below the level wins."""
    for level_str in sorted(ability.get("scaling", {}).keys(), key=int, reverse=True):
        if level >= int(level_str):
            return ability["scaling"][level_str].get("dice_count", base_count)
    return base_count


def _dice_text(spec, dice_count):
    bonus = spec.get("bonus", 0)
    extra = {"ability_modifier": " + mod", "level": " + level"}.get(bonus) or (f" + {bonus}" if bonus else "")
    return f"{dice_count}d{spec['dice_size']}{extra}"


def summarize_ability(ability, level):
    """Short stat lines for an ability at a level, e.g. ["2d10 + mod slashing", "Self: damage bonus +2"]."""
    lines = []
    damage, heal = ability.get("damage"), ability.get("heal")
    if damage:
        count = _scaled_dice_count(ability, damage["dice_count"], level)
        lines.append(f"{_dice_text(damage, count)} {damage.get('type', '')}".strip())
    if heal:
        count = heal["dice_count"] if damage else _scaled_dice_count(ability, heal["dice_count"], level)
        lines.append(f"Heal {_dice_text(heal, count)}")
    who = "Self" if ability.get("target") == "self" else "Enemy"
    for owner, effects in ((who, ability.get("effects", [])), ("Self", ability.get("self_effects", []))):
        for effect in effects:
            duration = effect.get("duration", 0)
            span = "whole fight" if duration == 0 else f"{duration} round{'s' if duration != 1 else ''}"
            lines.append(f"{owner}: {describe_effect(effect)}, {span}")
    return lines


def resolve_player_ability(char, ability, monster, player_effects, primary_mod):
    """Resolve a class ability used by the player against a monster.

    Mutates `char` (PP, HP), `monster` (HP, effects) and `player_effects`.

    Returns:
        list of battle-log lines, or None if the character can't afford the ability.
    """
    if char.power_points < ability["cost"]:
        return None
    char.power_points -= ability["cost"]

    log = []
    name = ability["name"]
    attack_method = ability["attack_method"]
    target = ability["target"]

    landed = True     # did the ability take full effect on the enemy?
    half = False      # spell save succeeded: half damage, no rider effects
    crit = False

    if target == "enemy" and attack_method in ("melee_attack", "spell_attack"):
        bonus = primary_mod + char.proficiency_bonus + get_effect_bonus(player_effects, "attack_bonus")
        effective_ac = monster.ac + get_effect_bonus(monster.effects, "ac")
        roll = resolve_attack_roll(bonus, effective_ac)
        landed, crit = roll["hit"], roll["crit"]
        if crit:
            log.append(f"{char.name} uses {name}! CRITICAL HIT! (natural 20 vs AC {effective_ac})")
        elif landed:
            log.append(f"{char.name} uses {name}! (Roll: {roll['total']} vs AC {effective_ac}) Hit!")
        else:
            log.append(f"{char.name} uses {name}! (Roll: {roll['total']} vs AC {effective_ac}) Miss!")

    elif target == "enemy" and attack_method == "spell_save":
        spell_dc = 8 + primary_mod + char.proficiency_bonus
        save_ability = ability.get("save_ability", "Dexterity")
        save_roll = Dice.roll_d20() + monster.get_mod(save_ability)
        if save_roll >= spell_dc:
            landed, half = False, True
            log.append(f"{char.name} casts {name}! ({monster.name} saves: {save_roll} vs DC {spell_dc}) Half damage!")
        else:
            log.append(f"{char.name} casts {name}! ({monster.name} fails save: {save_roll} vs DC {spell_dc})")

    else:
        log.append(f"{char.name} uses {name}!")

    # Damage
    if ability.get("damage") and target == "enemy" and (landed or half):
        dmg = ability["damage"]
        dice_count = _scaled_dice_count(ability, dmg["dice_count"], char.level)
        if crit:
            dice_count *= 2
        damage = roll_dice(dice_count, dmg["dice_size"]) + _bonus(dmg, primary_mod, char.level)
        damage = max(1, damage) + get_effect_bonus(player_effects, "damage_bonus")
        if half:
            damage = max(1, damage // 2)
        dr = get_effect_bonus(monster.effects, "damage_reduction")
        damage = max(1, damage - dr)
        monster.hp = max(0, monster.hp - damage)
        log.append(f"  {name} deals {damage} {dmg.get('type', '')} damage!".replace("  damage", " damage"))

    # Healing
    if ability.get("heal"):
        heal = ability["heal"]
        heal_dice = heal["dice_count"]
        if not ability.get("damage"):   # `scaling` belongs to the damage when there is one
            heal_dice = _scaled_dice_count(ability, heal_dice, char.level)
        amount = roll_dice(heal_dice, heal["dice_size"]) + _bonus(heal, primary_mod, char.level)
        amount = max(1, amount)
        old_hp = char.current_hit_points
        char.current_hit_points = min(char.max_hit_points, old_hp + amount)
        healed = char.current_hit_points - old_hp
        if healed > 0:
            log.append(f"  {char.name} heals for {healed} HP!")

    # Effects: self-buffs always apply; enemy riders need the ability to land
    for effect in ability.get("effects", []):
        eff = {"stat": effect["stat"], "value": effect["value"],
               "duration": effect["duration"], "source": name}
        if target == "enemy":
            if not landed:
                continue
            if eff["stat"] == "stun" and monster.is_boss:
                log.append(f"  {monster.name} shrugs off the stun!")
                continue
            monster.effects.append(eff)
            log.append(f"  {monster.name}: {describe_effect(eff)}")
        else:
            player_effects.append(eff)
            log.append(f"  {char.name}: {describe_effect(eff)}")

    # Self effects: the price (or perk) of an enemy-targeted ability, hit or miss
    for effect in ability.get("self_effects", []):
        eff = {"stat": effect["stat"], "value": effect["value"],
               "duration": effect["duration"], "source": name}
        player_effects.append(eff)
        log.append(f"  {char.name}: {describe_effect(eff)}")

    return log
