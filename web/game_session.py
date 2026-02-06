"""Session-based game state management for web UI."""

import sys
import json
import uuid
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Path to JSON data files
JSON_DIR = Path(__file__).parent.parent / "json"


def load_json(filename: str) -> dict:
    """Load a JSON file from the json directory."""
    with open(JSON_DIR / filename) as f:
        return json.load(f)


# Cached data loaders
_races_cache = None
_classes_cache = None
_weapons_cache = None
_campaign_cache = None


def get_races() -> dict:
    """Get all playable races with their bonuses."""
    global _races_cache
    if _races_cache is None:
        _races_cache = load_json("races.json")
    return _races_cache


def get_classes() -> dict:
    """Get all playable classes with their properties."""
    global _classes_cache
    if _classes_cache is None:
        _classes_cache = load_json("classes_properties.json")
    return _classes_cache


def get_weapons() -> dict:
    """Get all weapons from the catalog."""
    global _weapons_cache
    if _weapons_cache is None:
        _weapons_cache = load_json("weapon-catalog.json")
    return _weapons_cache


def get_campaign() -> dict:
    """Get the campaign data."""
    global _campaign_cache
    if _campaign_cache is None:
        _campaign_cache = load_json("campaign.json")
    return _campaign_cache


def get_all_weapons_flat() -> dict:
    """Get all weapons as a flat dictionary."""
    weapons = get_weapons()
    flat = {}
    for category, weapon_list in weapons.items():
        for name, data in weapon_list.items():
            flat[name] = {**data, "type": category}
    return flat


_armors_cache = None


def get_armors() -> dict:
    """Get all armors from the catalog."""
    global _armors_cache
    if _armors_cache is None:
        _armors_cache = load_json("armor_catalog.json")
    return _armors_cache


def get_all_armors_flat() -> dict:
    """Get all armors as a flat dictionary."""
    armors = get_armors()
    flat = {}
    for category, armor_list in armors.items():
        for name, data in armor_list.items():
            flat[name] = {**data, "type": category}
    return flat


@dataclass
class CharacterCreationState:
    """Tracks character creation progress."""
    race: Optional[str] = None
    class_name: Optional[str] = None
    name: Optional[str] = None
    weapon: Optional[str] = None
    armor: Optional[str] = None
    skills: list = field(default_factory=list)


@dataclass
class BattleState:
    """Tracks current battle state."""
    monster_name: str = ""
    monster_race: str = ""
    monster_level: int = 1
    monster_hp: int = 0
    monster_max_hp: int = 0
    monster_ac: int = 10
    monster_base_ac: int = 10
    monster_dex_modifier: int = 0
    monster_str_modifier: int = 0
    monster_proficiency_bonus: int = 1
    monster_weapon_name: str = ""
    monster_weapon_damage_die: int = 6
    monster_weapon_damage_dice_count: int = 1
    monster_weapon_properties: list = field(default_factory=list)
    round_count: int = 0
    initiative_order: list = field(default_factory=list)
    battle_log: list = field(default_factory=list)
    is_player_turn: bool = True
    is_active: bool = False


class GameSession:
    """Manages a single game session."""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.character = None
        self.character_creation = CharacterCreationState()
        self.battle = BattleState()
        self.current_location = None
        self.current_area = None
        self.act = None
        self.monster_kills = 0

    def to_dict(self) -> dict:
        """Serialize session to dictionary for storage."""
        # Store only location/area IDs to reduce cookie size
        location_name = self.current_location.get("name") if self.current_location else None
        area_id = self.current_area.get("id") if self.current_area else None
        act_num = self.act.get("number") if self.act else 1

        return {
            "session_id": self.session_id,
            "character": self._serialize_character(),
            "character_creation": {
                "race": self.character_creation.race,
                "class_name": self.character_creation.class_name,
                "name": self.character_creation.name,
                "weapon": self.character_creation.weapon,
                "armor": self.character_creation.armor,
                "skills": self.character_creation.skills,
            },
            "battle": {
                "monster_name": self.battle.monster_name,
                "monster_race": self.battle.monster_race,
                "monster_level": self.battle.monster_level,
                "monster_hp": self.battle.monster_hp,
                "monster_max_hp": self.battle.monster_max_hp,
                "monster_ac": self.battle.monster_ac,
                "monster_base_ac": self.battle.monster_base_ac,
                "monster_dex_modifier": self.battle.monster_dex_modifier,
                "monster_str_modifier": self.battle.monster_str_modifier,
                "monster_proficiency_bonus": self.battle.monster_proficiency_bonus,
                "monster_weapon_name": self.battle.monster_weapon_name,
                "monster_weapon_damage_die": self.battle.monster_weapon_damage_die,
                "monster_weapon_damage_dice_count": self.battle.monster_weapon_damage_dice_count,
                "monster_weapon_properties": self.battle.monster_weapon_properties,
                "round_count": self.battle.round_count,
                "initiative_order": self.battle.initiative_order,
                "battle_log": self.battle.battle_log[-5:],  # Only keep last 5 log entries
                "is_player_turn": self.battle.is_player_turn,
                "is_active": self.battle.is_active,
            },
            "location_name": location_name,
            "area_id": area_id,
            "act_num": act_num,
            "monster_kills": self.monster_kills,
        }

    def _get_weapon_name(self, c) -> Optional[str]:
        """Get the weapon name from character, handling enum keys."""
        from character import WeaponSlot
        weapon = c.weapon_slots.get(WeaponSlot.MAIN_HAND)
        return weapon.name if weapon else None

    def _get_armor_name(self, c) -> Optional[str]:
        """Get the armor name from character, handling enum keys."""
        from equipmentType import EquipmentType
        armor = c.equipment.get(EquipmentType.ARMOR)
        return armor.name if armor else None

    def _serialize_character(self) -> Optional[dict]:
        """Serialize character object to dict."""
        if not self.character:
            return None
        c = self.character
        return {
            "name": c.name,
            "race": c.race,
            "class_name": c.class_name,
            "level": c.level,
            "xp": c.xp,
            "gold": c.gold,
            "current_hit_points": c.current_hit_points,
            "max_hit_points": c.max_hit_points,
            "armor_class": c.armor_class,
            "strength_score": c.strength_score,
            "strength_modifier": c.strength_modifier,
            "dexterity_score": c.dexterity_score,
            "dexterity_modifier": c.dexterity_modifier,
            "constitution_score": c.constitution_score,
            "constitution_modifier": c.constitution_modifier,
            "intelligence_score": c.intelligence_score,
            "intelligence_modifier": c.intelligence_modifier,
            "wisdom_score": c.wisdom_score,
            "wisdom_modifier": c.wisdom_modifier,
            "charisma_score": c.charisma_score,
            "charisma_modifier": c.charisma_modifier,
            "weapon": self._get_weapon_name(c),
            "armor": self._get_armor_name(c),
            "inventory": [{"name": item.name, "description": item.description} for item in c.inventory],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameSession":
        """Deserialize session from dictionary."""
        session = cls(data.get("session_id"))
        session.monster_kills = data.get("monster_kills", 0)

        # Restore location from campaign data
        campaign = get_campaign()
        act_num = data.get("act_num", 1)
        location_name = data.get("location_name")
        area_id = data.get("area_id")

        # Find the act
        for act in campaign.get("acts", []):
            if act.get("number") == act_num:
                session.act = act
                break
        if not session.act and campaign.get("acts"):
            session.act = campaign["acts"][0]

        # Find the location
        if session.act and location_name:
            for loc in session.act.get("locations", []):
                if loc.get("name") == location_name:
                    session.current_location = loc
                    break

        # Find the area
        if session.current_location and area_id:
            for area in session.current_location.get("areas", []):
                if area.get("id") == area_id:
                    session.current_area = area
                    break

        # Restore character creation state
        cc_data = data.get("character_creation", {})
        session.character_creation = CharacterCreationState(
            race=cc_data.get("race"),
            class_name=cc_data.get("class_name"),
            name=cc_data.get("name"),
            weapon=cc_data.get("weapon"),
            armor=cc_data.get("armor"),
            skills=cc_data.get("skills", []),
        )

        # Restore battle state
        battle_data = data.get("battle", {})
        session.battle = BattleState(
            monster_name=battle_data.get("monster_name", ""),
            monster_race=battle_data.get("monster_race", ""),
            monster_level=battle_data.get("monster_level", 1),
            monster_hp=battle_data.get("monster_hp", 0),
            monster_max_hp=battle_data.get("monster_max_hp", 0),
            monster_ac=battle_data.get("monster_ac", 10),
            monster_base_ac=battle_data.get("monster_base_ac", 10),
            monster_dex_modifier=battle_data.get("monster_dex_modifier", 0),
            monster_str_modifier=battle_data.get("monster_str_modifier", 0),
            monster_proficiency_bonus=battle_data.get("monster_proficiency_bonus", 1),
            monster_weapon_name=battle_data.get("monster_weapon_name", ""),
            monster_weapon_damage_die=battle_data.get("monster_weapon_damage_die", 6),
            monster_weapon_damage_dice_count=battle_data.get("monster_weapon_damage_dice_count", 1),
            monster_weapon_properties=battle_data.get("monster_weapon_properties", []),
            round_count=battle_data.get("round_count", 0),
            initiative_order=battle_data.get("initiative_order", []),
            battle_log=battle_data.get("battle_log", []),
            is_player_turn=battle_data.get("is_player_turn", True),
            is_active=battle_data.get("is_active", False),
        )

        # Restore character if creation data exists
        char_data = data.get("character")
        if char_data and cc_data.get("name"):
            session.character = session._restore_character(char_data, cc_data)

        return session

    def _restore_character(self, char_data: dict, cc_data: dict):
        """Restore a character object from serialized data."""
        try:
            from characterFactory import CharacterFactory
            from weaponFactory import WeaponFactory
            from items import HealingPotion
            from character import WeaponSlot

            # Recreate character using factory
            factory = CharacterFactory()
            character = factory.create_character(
                name=cc_data["name"],
                race=cc_data["race"],
                class_name=cc_data["class_name"]
            )

            # Restore state
            character.level = char_data.get("level", 1)
            character.xp = char_data.get("xp", 0)
            character.gold = char_data.get("gold", 0)
            character.current_hit_points = char_data.get("current_hit_points", character.max_hit_points)
            character.max_hit_points = char_data.get("max_hit_points", character.max_hit_points)
            character.armor_class = char_data.get("armor_class", character.armor_class)
            character.xp_to_next_level = character.level * 150

            # Restore weapon (use enum, not string)
            if cc_data.get("weapon"):
                weapon_factory = WeaponFactory()
                try:
                    weapon = weapon_factory.get_weapon_by_name(cc_data["weapon"])
                    character.equip_weapon(weapon, WeaponSlot.MAIN_HAND)
                except ValueError:
                    pass

            # Restore armor
            if cc_data.get("armor"):
                from armorFactory import ArmorFactory
                armor_factory = ArmorFactory()
                try:
                    armor = armor_factory.get_armor_by_name(cc_data["armor"])
                    character.equip(armor)
                except ValueError:
                    pass

            # Restore skills
            for skill in cc_data.get("skills", []):
                character.add_skill_proficiency(skill)

            # Restore inventory
            character.inventory = []
            for item_data in char_data.get("inventory", []):
                if "Healing Potion" in item_data["name"]:
                    # Parse healing amount from name or description
                    if "Minor" in item_data["name"]:
                        healing = 5
                    elif "Greater" in item_data["name"]:
                        healing = 20
                    elif "Small" in item_data["name"]:
                        healing = 10
                    elif "Medium" in item_data["name"]:
                        healing = 25
                    else:
                        healing = 10
                    character.add_item(HealingPotion(item_data["name"], healing))

            return character
        except Exception as e:
            print(f"Error restoring character: {e}")
            return None


def get_session(request) -> GameSession:
    """Get or create a GameSession from the request session."""
    session_data = request.session.get("game_session")
    if session_data:
        return GameSession.from_dict(session_data)
    return GameSession()


def save_session(request, session: GameSession):
    """Save GameSession to the request session."""
    request.session["game_session"] = session.to_dict()
