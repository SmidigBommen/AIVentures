"""Serializable combatant state for battle — replaces flat monster fields."""

from dataclasses import dataclass, field


@dataclass
class WeaponState:
    """Serializable weapon data for combat."""
    name: str = ""
    damage_die: int = 6
    damage_dice_count: int = 1
    properties: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "damage_die": self.damage_die,
            "damage_dice_count": self.damage_dice_count,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WeaponState":
        return cls(
            name=data.get("name", ""),
            damage_die=data.get("damage_die", 6),
            damage_dice_count=data.get("damage_dice_count", 1),
            properties=data.get("properties", []),
        )

    @classmethod
    def from_weapon(cls, weapon) -> "WeaponState":
        """Create from a domain Weapon object."""
        return cls(
            name=weapon.name,
            damage_die=weapon.damage_die,
            damage_dice_count=weapon.damage_dice_count,
            properties=weapon.properties,
        )


@dataclass
class CombatantState:
    """Serializable combatant for battle (works for both monsters and players)."""
    name: str = ""
    race: str = ""
    level: int = 1
    hp: int = 0
    max_hp: int = 0
    ac: int = 10
    base_ac: int = 10
    str_mod: int = 0
    dex_mod: int = 0
    proficiency: int = 1
    weapon: WeaponState = field(default_factory=WeaponState)
    effects: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "race": self.race,
            "level": self.level,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "base_ac": self.base_ac,
            "str_mod": self.str_mod,
            "dex_mod": self.dex_mod,
            "proficiency": self.proficiency,
            "weapon": self.weapon.to_dict(),
            "effects": self.effects,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CombatantState":
        return cls(
            name=data.get("name", ""),
            race=data.get("race", ""),
            level=data.get("level", 1),
            hp=data.get("hp", 0),
            max_hp=data.get("max_hp", 0),
            ac=data.get("ac", 10),
            base_ac=data.get("base_ac", 10),
            str_mod=data.get("str_mod", 0),
            dex_mod=data.get("dex_mod", 0),
            proficiency=data.get("proficiency", 1),
            weapon=WeaponState.from_dict(data.get("weapon", {})),
            effects=data.get("effects", []),
        )

    @classmethod
    def from_monster(cls, monster) -> "CombatantState":
        """Create from a domain Monster object."""
        return cls(
            name=monster.name,
            race=monster.race,
            level=monster.level,
            hp=monster.current_hit_points,
            max_hp=monster.max_hit_points,
            ac=monster.armor_class,
            base_ac=monster.base_ac,
            str_mod=monster.strength_modifier,
            dex_mod=monster.dexterity_modifier,
            proficiency=monster.proficiency_bonus,
            weapon=WeaponState.from_weapon(monster.weapon),
            effects=[],
        )

    def reset_ac(self):
        """Reset AC to base + dex (clears defend bonus)."""
        self.ac = self.base_ac + self.dex_mod
