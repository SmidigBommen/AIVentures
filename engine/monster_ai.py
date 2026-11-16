"""Monster decision-making and special ability resolution.

Monster abilities are data-driven (json/monster_abilities.json). Each ability:

    {
      "name": "Fire Breath",
      "text": "{name} exhales a cone of searing flame!",
      "kind": "attack" | "save" | "self",
      "stat": "con",                  # modifier used for the attack roll / save DC
      "save_ability": "Dexterity",    # kind == "save" only
      "half_on_save": true,
      "damage": {"dice_count": 2, "dice_size": 6, "type": "fire", "scale_levels": 4},
      "lifesteal": true,              # monster heals for the damage dealt
      "heal": {"dice_count": 1, "dice_size": 8, "level_bonus": true},
      "effects": [{"stat": "burn", "value": 2, "duration": 2, "target": "player"}],
      "cooldown": 3,
      "use_below_hp": 0.6             # only considered at or below this HP fraction
    }
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from engine.combat import resolve_attack_roll, roll_dice
from engine.effects import get_effect_bonus, describe_effect

ABILITY_CHANCE = 0.3
BOSS_ABILITY_CHANCE = 0.5
HEAL_CHANCE = 0.75


def available_abilities(monster, catalog):
    """Ability ids the monster could use right now (known, off cooldown, HP gate met)."""
    hp_fraction = monster.hp / monster.max_hp if monster.max_hp else 1
    result = []
    for ability_id in monster.abilities:
        ability = catalog.get(ability_id)
        if not ability:
            continue
        if monster.cooldowns.get(ability_id, 0) > 0:
            continue
        if hp_fraction > ability.get("use_below_hp", 1.0):
            continue
        # Don't re-cast a self-buff that is still running
        if ability["kind"] == "self" and not ability.get("heal"):
            if any(e["source"] == ability["name"] for e in monster.effects):
                continue
        result.append(ability_id)
    return result


def choose_monster_action(monster, catalog, player_hp_fraction=1.0):
    """Pick the monster's action for this turn.

    Returns:
        (action, ability_id) where action is "attack", "defend" or "ability".
    """
    usable = available_abilities(monster, catalog)
    hp_fraction = monster.hp / monster.max_hp if monster.max_hp else 1

    # Wounded monsters reach for healing first
    heals = [a for a in usable if catalog[a].get("heal")]
    if heals and random.random() < HEAL_CHANCE:
        return "ability", random.choice(heals)

    others = [a for a in usable if not catalog[a].get("heal")]
    # Low-level rabble mostly just swings; craftier foes lean on their tricks
    chance = BOSS_ABILITY_CHANCE if monster.is_boss else min(ABILITY_CHANCE, 0.1 + 0.03 * monster.level)
    if others and random.random() < chance:
        return "ability", random.choice(others)

    # Smell blood: never turtle when the player is nearly down
    if player_hp_fraction <= 0.3:
        return "attack", None

    defend_chance = 0.35 if hp_fraction <= 0.3 else 0.15
    if random.random() < defend_chance:
        return "defend", None
    return "attack", None


def tick_cooldowns(monster):
    """Reduce every running cooldown by one round."""
    monster.cooldowns = {k: v - 1 for k, v in monster.cooldowns.items() if v > 1}


def _ability_damage(monster, ability, crit=False):
    dmg = ability["damage"]
    dice_count = dmg["dice_count"]
    scale = dmg.get("scale_levels")
    if scale:
        dice_count += monster.level // scale
    if crit:
        dice_count *= 2
    total = roll_dice(dice_count, dmg["dice_size"])
    total += monster.get_mod(ability.get("stat", "str"))
    return max(1, total + get_effect_bonus(monster.effects, "damage_bonus"))


def resolve_monster_ability(monster, ability_id, ability, player_ac, player_effects, player_save_mods):
    """Resolve a monster special ability against the player.

    Mutates `monster` (healing, self-effects, cooldown) and `player_effects`
    (debuffs/conditions). The caller applies the returned damage to the player.

    Args:
        player_ac: the player's base armor class (effects are added here)
        player_effects: the player's active effect list (appended to)
        player_save_mods: {"strength": int, ...} total saving throw modifiers

    Returns:
        dict with keys: damage (int), log (list[str]), landed (bool), crit (bool),
        half (bool — a save succeeded but half the damage still applies)
    """
    log = [ability.get("text", "{name} uses {ability}!").format(name=monster.name, ability=ability["name"])]
    kind = ability["kind"]
    stat_mod = monster.get_mod(ability.get("stat", "str"))
    damage = 0
    landed = True
    half = False
    crit = False

    if kind == "attack":
        bonus = stat_mod + monster.proficiency + get_effect_bonus(monster.effects, "attack_bonus")
        effective_ac = player_ac + get_effect_bonus(player_effects, "ac")
        roll = resolve_attack_roll(bonus, effective_ac)
        landed, crit = roll["hit"], roll["crit"]
        if roll["crit"]:
            log.append(f"  CRITICAL HIT! (natural 20 vs AC {effective_ac})")
        elif landed:
            log.append(f"  (Roll: {roll['total']} vs AC {effective_ac}) It connects!")
        else:
            log.append(f"  (Roll: {roll['total']} vs AC {effective_ac}) You evade it — the attack misses!")
        if landed and ability.get("damage"):
            damage = _ability_damage(monster, ability, crit=roll["crit"])

    elif kind == "save":
        dc = 8 + monster.proficiency + stat_mod
        save_ability = ability.get("save_ability", "Dexterity")
        save_roll = Dice.roll_d20() + player_save_mods.get(save_ability.lower(), 0)
        if save_roll >= dc:
            landed = False
            half = bool(ability.get("half_on_save"))
            log.append(f"  {save_ability} save: {save_roll} vs DC {dc} — you resist!")
        else:
            log.append(f"  {save_ability} save: {save_roll} vs DC {dc} — you fail!")
        if ability.get("damage") and (landed or half):
            damage = _ability_damage(monster, ability)
            if half:
                damage = max(1, damage // 2)

    if damage:
        dr = get_effect_bonus(player_effects, "damage_reduction")
        damage = max(1, damage - dr)
        dmg_type = ability["damage"].get("type", "")
        log.append(f"  {ability['name']} deals {damage} {dmg_type} damage!".replace("  damage", " damage"))
        if ability.get("lifesteal"):
            healed = min(monster.max_hp - monster.hp, damage)
            if healed > 0:
                monster.hp += healed
                log.append(f"  {monster.name} drains {healed} HP from you!")

    if ability.get("heal"):
        heal = ability["heal"]
        amount = roll_dice(heal["dice_count"], heal["dice_size"])
        if heal.get("level_bonus"):
            amount += monster.level
        healed = min(monster.max_hp - monster.hp, amount)
        monster.hp += healed
        log.append(f"  {monster.name} heals for {healed} HP!")

    for effect in ability.get("effects", []):
        on_self = effect.get("target", "player") == "self"
        if not on_self and not landed:
            continue
        duration = effect["duration"]
        # The monster acts last in a round, so a timed effect applied now would lose
        # a round to the end-of-round tick before it ever mattered.
        if duration > 0:
            duration += 1
        eff = {"stat": effect["stat"], "value": effect["value"],
               "duration": duration, "source": ability["name"]}
        if on_self:
            monster.effects.append(eff)
            log.append(f"  {monster.name}: {describe_effect(eff)}")
        else:
            player_effects.append(eff)
            log.append(f"  You are afflicted: {describe_effect(eff)}")

    if ability.get("cooldown"):
        # +1 because cooldowns tick at the end of the round the ability was used in
        monster.cooldowns[ability_id] = ability["cooldown"] + 1

    return {"damage": damage, "log": log, "landed": landed, "crit": crit, "half": half}
