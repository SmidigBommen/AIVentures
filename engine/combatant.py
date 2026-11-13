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
    con_mod: int = 0
    int_mod: int = 0
    wis_mod: int = 0
    cha_mod: int = 0
    proficiency: int = 1
    weapon: WeaponState = field(default_factory=WeaponState)
    effects: list = field(default_factory=list)
    abilities: list = field(default_factory=list)    # monster ability ids
    cooldowns: dict = field(default_factory=dict)    # {ability_id: rounds remaining}
    boss_id: str = ""                                # key into bosses.json ("" = regular monster)
    enraged: bool = False                            # bosses enrage at half health

    @property
    def is_boss(self) -> bool:
        return bool(self.boss_id)

    def get_mod(self, ability: str) -> int:
        """Ability modifier by name — accepts 'Dexterity', 'dexterity' or 'dex'."""
        return getattr(self, f"{ability.lower()[:3]}_mod", 0)

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
            "con_mod": self.con_mod,
            "int_mod": self.int_mod,
            "wis_mod": self.wis_mod,
            "cha_mod": self.cha_mod,
            "proficiency": self.proficiency,
            "weapon": self.weapon.to_dict(),
            "effects": self.effects,
            "abilities": self.abilities,
            "cooldowns": self.cooldowns,
            "boss_id": self.boss_id,
            "enraged": self.enraged,
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
            con_mod=data.get("con_mod", 0),
            int_mod=data.get("int_mod", 0),
            wis_mod=data.get("wis_mod", 0),
            cha_mod=data.get("cha_mod", 0),
            proficiency=data.get("proficiency", 1),
            weapon=WeaponState.from_dict(data.get("weapon", {})),
            effects=data.get("effects", []),
            abilities=data.get("abilities", []),
            cooldowns=data.get("cooldowns", {}),
            boss_id=data.get("boss_id", ""),
            enraged=data.get("enraged", False),
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
            con_mod=monster.constitution_modifier,
            int_mod=monster.intelligence_modifier,
            wis_mod=monster.wisdom_modifier,
            cha_mod=monster.charisma_modifier,
            proficiency=monster.proficiency_bonus,
            weapon=WeaponState.from_weapon(monster.weapon),
            effects=[],
        )

    @classmethod
    def from_boss(cls, boss_id: str, boss: dict) -> "CombatantState":
        """Create from a bosses.json definition (hand-authored stats, no factory)."""
        scores = boss.get("scores", {})

        def mod(name):
            return (scores.get(name, 10) - 10) // 2

        weapon = boss.get("weapon", {})
        return cls(
            name=boss.get("name", boss_id),
            race=boss.get("type", "Boss"),
            level=boss.get("level", 1),
            hp=boss["hp"],
            max_hp=boss["hp"],
            ac=boss.get("ac", 12),
            # reset_ac() recomputes base_ac + dex_mod, so store AC net of DEX
            base_ac=boss.get("ac", 12) - mod("dex"),
            str_mod=mod("str"),
            dex_mod=mod("dex"),
            con_mod=mod("con"),
            int_mod=mod("int"),
            wis_mod=mod("wis"),
            cha_mod=mod("cha"),
            # Same progression every Entity uses (see Entity.update_proficiency_bonus)
            proficiency=boss.get("proficiency", 1 + boss.get("level", 1) // 4),
            weapon=WeaponState(
                name=weapon.get("name", "Claws"),
                damage_die=weapon.get("damage_die", 8),
                damage_dice_count=weapon.get("damage_dice_count", 1),
                properties=weapon.get("properties", []),
            ),
            effects=[],
            abilities=list(boss.get("abilities", [])),
            boss_id=boss_id,
        )

    def reset_ac(self):
        """Reset AC to base + dex (clears defend bonus)."""
        self.ac = self.base_ac + self.dex_mod
