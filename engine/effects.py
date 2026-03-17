"""Active effect management for combat buffs/debuffs."""


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


def clear_effects(effects=None):
    """Return an empty effects list."""
    return []
