"""Structured record of what happened in a battle turn.

The battle log is prose for the player to read. The battle screen also needs to
*play* a turn back — who acted, whether it landed, how much HP moved — so each
step of a turn is recorded as an event dict:

    {"actor": "player" | "monster",
     "kind": "attack" | "ability" | "defend" | "item" | "flee" | "stunned"
             | "condition" | "enrage",
     "name": label shown on screen ("Fireball", "Longsword"),
     "outcome": "hit" | "crit" | "miss" | "half" | None,
     "fx": visual effect key (a damage type, or "heal" / "buff" / "shield" ...),
     "ranged": True when the actor stays put and something flies at the target,
     "player": HP change of the player during this step,
     "monster": HP change of the monster during this step}

HP changes are measured between snapshots, so they are right whatever the
engine did in between (damage reduction, lifesteal, overheal caps).
"""

# Effect keys the battle screen knows how to draw; anything else falls back to "impact"
FX_KEYS = {
    "slashing", "piercing", "bludgeoning", "fire", "cold", "lightning", "poison", "acid",
    "radiant", "necrotic", "force", "psychic", "thunder",
    "heal", "buff", "debuff", "shield", "stun", "rage", "bleed", "burn", "regen", "impact",
}


class TurnRecorder:
    """Collects the events of one turn."""

    def __init__(self, player_hp: int, monster_hp: int):
        self.events = []
        self._player_hp = player_hp
        self._monster_hp = monster_hp

    def add(self, actor, kind, player_hp, monster_hp, name="", outcome=None, fx="impact",
            ranged=False):
        """Record a step. `player_hp` / `monster_hp` are the values after it."""
        event = {
            "actor": actor,
            "kind": kind,
            "name": name,
            "outcome": outcome,
            "fx": fx if fx in FX_KEYS else "impact",
            "ranged": bool(ranged),
            "player": player_hp - self._player_hp,
            "monster": monster_hp - self._monster_hp,
        }
        self._player_hp, self._monster_hp = player_hp, monster_hp
        self.events.append(event)
        return event


def ability_fx(ability) -> str:
    """Effect key for a player or monster ability definition."""
    damage = ability.get("damage")
    if damage:
        return damage.get("type") or "impact"
    if ability.get("heal"):
        return "heal"
    effects = ability.get("effects", [])
    if effects:
        first = effects[0]
        if first["stat"] in ("poison", "burn", "bleed", "stun", "regen"):
            return first["stat"]
        on_self = ability.get("target") == "self" or first.get("target") == "self" \
            or ability.get("kind") == "self"
        if on_self:
            return "shield" if first["stat"] in ("ac", "damage_reduction") else "buff"
        return "debuff"
    return "buff"


def outcome_of(hit: bool, crit: bool = False, half: bool = False):
    if crit:
        return "crit"
    if hit:
        return "hit"
    return "half" if half else "miss"
