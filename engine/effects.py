"""Active effect management for combat buffs/debuffs and conditions.

An effect is a dict: {"stat", "value", "duration", "source"}.

Stat modifiers (summed by get_effect_bonus): ac, attack_bonus, damage_bonus,
damage_reduction.

Conditions (resolved once per round by resolve_round_conditions):
  - poison / burn / bleed: the bearer takes `value` damage at the end of each round
  - regen: the bearer heals `value` HP at the end of each round
  - stun: the bearer loses their turn while the effect is active
"""

DOT_STATS = ("poison", "burn", "bleed")
CONDITION_STATS = DOT_STATS + ("regen", "stun")

CONDITION_LABELS = {
    "poison": "Poisoned",
    "burn": "Burning",
    "bleed": "Bleeding",
    "regen": "Regenerating",
    "stun": "Stunned",
}


def get_effect_bonus(effects, stat):
    """Sum all active effect bonuses for a given stat."""
    return sum(e["value"] for e in effects if e["stat"] == stat)


def tick_effects(effects):
    """Decrement durations and remove expired effects.

    Duration 0 = lasts entire combat (permanent until cleared).
    Duration 1 = expires this round (removed).
    Duration >1 = decremented by 1.
    """
    remaining = []
    for e in effects:
        if e["duration"] == 0:
            remaining.append(e)
        elif e["duration"] > 1:
            remaining.append({**e, "duration": e["duration"] - 1})
    return remaining


def apply_effect(effects, stat, value, duration, source):
    """Add a new effect to an effects list. Returns the updated list."""
    effects.append({
        "stat": stat,
        "value": value,
        "duration": duration,
        "source": source,
    })
    return effects


def clear_effects():
    """Return an empty effects list."""
    return []


def is_stunned(effects):
    """True if any stun effect is active."""
    return any(e["stat"] == "stun" for e in effects)


def resolve_round_conditions(effects):
    """Total up end-of-round damage-over-time and regeneration.

    Returns:
        dict with keys: damage (int), heal (int),
                        sources (list of (stat, value) for log messages)
    """
    damage = 0
    heal = 0
    sources = []
    for e in effects:
        if e["stat"] in DOT_STATS:
            damage += e["value"]
            sources.append((e["stat"], e["value"]))
        elif e["stat"] == "regen":
            heal += e["value"]
            sources.append(("regen", e["value"]))
    return {"damage": damage, "heal": heal, "sources": sources}


def describe_effect(effect):
    """Human-readable one-liner for an effect (used in logs and tooltips)."""
    stat = effect["stat"]
    if stat in DOT_STATS:
        return f"{CONDITION_LABELS[stat]} ({effect['value']} damage/round)"
    if stat == "regen":
        return f"Regenerating ({effect['value']} HP/round)"
    if stat == "stun":
        return "Stunned"
    return f"{stat.replace('_', ' ')} {effect['value']:+d}"
