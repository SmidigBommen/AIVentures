"""Tests for GameSession serialization roundtrips — the highest-risk code path.

Every HTTP request deserializes the session from JSON and every response serializes
it back. If anything is lost in this roundtrip, the player loses game state silently.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web.game_session import GameSession, BattleState, CharacterCreationState, get_campaign
from engine.combatant import CombatantState, WeaponState
from characterFactory import CharacterFactory
from weaponFactory import WeaponFactory
from armorFactory import ArmorFactory
from items import HealingPotion, QuestItem
from character import WeaponSlot


def _make_session_with_character():
    """Create a GameSession with a fully-equipped character for testing."""
    session = GameSession("test-session-id")
    factory = CharacterFactory()
    char = factory.create_character("TestHero", "Elf", "Wizard")

    # Equip weapon
    wf = WeaponFactory()
    dagger = wf.get_weapon_by_name("Dagger")
    char.equip_weapon(dagger, WeaponSlot.MAIN_HAND)

    # Equip armor
    af = ArmorFactory()
    leather = af.get_armor_by_name("Leather")
    char.equip(leather)

    # Set some state
    char.level = 3
    char.xp = 75
    char.gold = 42
    char.current_hit_points = 15
    char.max_hit_points = 22
    char.power_points = 5
    char.max_power_points = 8
    char.active_effects = [{"stat": "ac", "value": 1, "duration": 0, "source": "test"}]
    char.add_skill_proficiency("Arcana")
    char.add_skill_proficiency("Perception")

    # Add inventory items
    char.add_item(HealingPotion("Minor Healing Potion", 5))
    char.add_item(HealingPotion("Greater Healing Potion", 20))
    char.add_item(QuestItem("Goblin Ear", "A severed ear", "quest_goblin"))

    session.character = char
    session.character_creation = CharacterCreationState(
        race="Elf", class_name="Wizard", name="TestHero",
        weapon="Dagger", armor="Leather", portrait="/static/images/player_wizard.png",
        skills=["Arcana", "Perception"],
    )

    # Set location
    campaign = get_campaign()
    session.act = campaign["acts"][0]
    session.current_location = session.act["locations"][0]
    session.current_area = session.current_location["areas"][0]

    # Set quest state
    session.active_quests = {
        "q1": {"progress": 2, "status": "active"},
        "q2": {"progress": 5, "status": "ready"},
    }
    session.completed_quests = ["q0"]
    session.monster_kills = 7
    session.kills_at_last_restock = 0

    # Set shop state
    session.shop_inventory = [{"name": "Potion", "healing": 5, "price": 10, "quantity": 3}]
    session.haggled_items = {"0": 15}

    # Set flash
    session.set_flash("shop_message", "Hello!")

    return session


class TestSessionRoundtrip:
    def test_empty_session_roundtrip(self):
        session = GameSession("empty-id")
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        assert restored.session_id == "empty-id"
        assert restored.character is None
        assert restored.battle.is_active is False
        assert restored.monster_kills == 0

    def test_full_session_roundtrip(self):
        """The big test: serialize a full session with character, quests, shop, etc."""
        session = _make_session_with_character()
        d = session.to_dict()

        # Verify it's JSON-serializable (this is what actually gets written to disk)
        json_str = json.dumps(d)
        d2 = json.loads(json_str)

        restored = GameSession.from_dict(d2)

        # Session metadata
        assert restored.session_id == "test-session-id"
        assert restored.monster_kills == 7
        assert restored.kills_at_last_restock == 0

        # Character identity
        char = restored.character
        assert char is not None
        assert char.name == "TestHero"
        assert char.race == "Elf"
        assert char.class_name == "Wizard"

        # Character stats
        assert char.level == 3
        assert char.xp == 75
        assert char.gold == 42
        assert char.current_hit_points == 15
        assert char.max_hit_points == 22

        # Power points
        assert char.power_points == 5
        assert char.max_power_points >= 1  # recalculated from level/class

        # Equipment
        weapon = char.weapon_slots.get(WeaponSlot.MAIN_HAND)
        assert weapon is not None
        assert weapon.name == "Dagger"

        # Skills
        assert "Arcana" in char.skill_proficiencies
        assert "Perception" in char.skill_proficiencies

    def test_inventory_types_preserved(self):
        """Verify that item types (weapon, armor, potion, quest_item) survive roundtrip."""
        session = _make_session_with_character()

        # Add a weapon and armor to inventory
        wf = WeaponFactory()
        session.character.add_item(wf.get_weapon_by_name("Shortbow"))
        af = ArmorFactory()
        session.character.add_item(af.get_armor_by_name("Chain Shirt"))

        d = session.to_dict()
        json_str = json.dumps(d)
        d2 = json.loads(json_str)
        restored = GameSession.from_dict(d2)

        inv = restored.character.inventory
        types = [type(item).__name__ for item in inv]
        assert "HealingPotion" in types
        assert "QuestItem" in types
        assert "Weapon" in types
        assert "Armor" in types

    def test_quest_item_quest_id_preserved(self):
        session = _make_session_with_character()
        d = session.to_dict()
        restored = GameSession.from_dict(json.loads(json.dumps(d)))
        quest_items = [i for i in restored.character.inventory if isinstance(i, QuestItem)]
        assert len(quest_items) >= 1
        assert quest_items[0].quest_id == "quest_goblin"

    def test_quest_state_preserved(self):
        session = _make_session_with_character()
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        assert restored.active_quests == {"q1": {"progress": 2, "status": "active"},
                                          "q2": {"progress": 5, "status": "ready"}}
        assert restored.completed_quests == ["q0"]

    def test_shop_state_preserved(self):
        session = _make_session_with_character()
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        assert restored.shop_inventory is not None
        assert len(restored.shop_inventory) == 1
        assert restored.haggled_items == {"0": 15}

    def test_flash_messages_preserved(self):
        session = _make_session_with_character()
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        assert restored.pop_flash("shop_message") == "Hello!"

    def test_location_restored(self):
        session = _make_session_with_character()
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        assert restored.act is not None
        assert restored.current_location is not None
        assert restored.current_area is not None
        assert restored.current_location["name"] == session.current_location["name"]
        assert restored.current_area["id"] == session.current_area["id"]

    def test_character_creation_state_preserved(self):
        session = _make_session_with_character()
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        cc = restored.character_creation
        assert cc.race == "Elf"
        assert cc.class_name == "Wizard"
        assert cc.name == "TestHero"
        assert cc.weapon == "Dagger"
        assert cc.armor == "Leather"
        assert cc.portrait == "/static/images/player_wizard.png"
        assert cc.skills == ["Arcana", "Perception"]


class TestBattleStateRoundtrip:
    def test_battle_state_roundtrip(self):
        session = GameSession("battle-test")
        session.battle = BattleState(
            monster=CombatantState(
                name="Gruk", race="Orc", level=3,
                hp=25, max_hp=30, ac=14, base_ac=12,
                str_mod=3, dex_mod=1, proficiency=2,
                weapon=WeaponState(name="Greataxe", damage_die=12, damage_dice_count=1, properties=[]),
                effects=[{"stat": "ac", "value": 2, "duration": 0, "source": "shield"}],
            ),
            round_count=4,
            initiative_order=[("player", 18), ("monster", 12)],
            battle_log=["Round 1 begins", "Player attacks"],
            is_player_turn=False,
            is_active=True,
            player_effects=[{"stat": "damage_bonus", "value": 3, "duration": 2, "source": "rage"}],
        )
        d = session.to_dict()
        json_str = json.dumps(d)
        restored = GameSession.from_dict(json.loads(json_str))

        b = restored.battle
        assert b.is_active is True
        assert b.round_count == 4
        assert b.is_player_turn is False
        assert b.monster_name == "Gruk"
        assert b.monster_race == "Orc"
        assert b.monster_hp == 25
        assert b.monster_max_hp == 30
        assert b.monster_ac == 14
        assert b.monster_base_ac == 12
        assert b.monster_str_modifier == 3
        assert b.monster_dex_modifier == 1
        assert b.monster_proficiency_bonus == 2
        assert b.monster_weapon_name == "Greataxe"
        assert b.monster_weapon_damage_die == 12
        assert len(b.monster_effects) == 1
        assert len(b.player_effects) == 1
        assert len(b.battle_log) == 2

    def test_legacy_flat_format_still_loads(self):
        """Old session files use flat monster_* fields — verify backward compat."""
        legacy_data = {
            "session_id": "legacy",
            "battle": {
                "monster_name": "Old Goblin",
                "monster_race": "Goblin",
                "monster_level": 2,
                "monster_hp": 10,
                "monster_max_hp": 15,
                "monster_ac": 12,
                "monster_base_ac": 10,
                "monster_dex_modifier": 1,
                "monster_str_modifier": 0,
                "monster_proficiency_bonus": 1,
                "monster_weapon_name": "Club",
                "monster_weapon_damage_die": 4,
                "monster_weapon_damage_dice_count": 1,
                "monster_weapon_properties": [],
                "round_count": 2,
                "initiative_order": [],
                "battle_log": [],
                "is_player_turn": True,
                "is_active": True,
                "monster_effects": [],
                "player_effects": [],
            },
        }
        restored = GameSession.from_dict(legacy_data)
        assert restored.battle.monster_name == "Old Goblin"
        assert restored.battle.monster_race == "Goblin"
        assert restored.battle.monster_hp == 10
        assert restored.battle.monster_ac == 12
        assert restored.battle.monster_weapon_name == "Club"
        assert restored.battle.is_active is True

    def test_empty_battle_roundtrip(self):
        session = GameSession("no-battle")
        d = session.to_dict()
        restored = GameSession.from_dict(d)
        assert restored.battle.is_active is False
        assert restored.battle.monster_name == ""
        assert restored.battle.monster_hp == 0


class TestBattleStateCompatProperties:
    """Verify that the backward-compatible properties on BattleState work correctly."""

    def test_monster_hp_getter_setter(self):
        bs = BattleState(monster=CombatantState(hp=20))
        assert bs.monster_hp == 20
        bs.monster_hp = 15
        assert bs.monster_hp == 15
        assert bs.monster.hp == 15

    def test_monster_ac_getter_setter(self):
        bs = BattleState(monster=CombatantState(ac=14))
        assert bs.monster_ac == 14
        bs.monster_ac = 16
        assert bs.monster_ac == 16

    def test_monster_effects_getter_setter(self):
        bs = BattleState(monster=CombatantState())
        assert bs.monster_effects == []
        bs.monster_effects = [{"stat": "ac", "value": 2, "duration": 1, "source": "x"}]
        assert len(bs.monster_effects) == 1
        assert bs.monster.effects == bs.monster_effects

    def test_weapon_properties_proxy(self):
        ws = WeaponState(name="Rapier", damage_die=8, properties=["finesse"])
        bs = BattleState(monster=CombatantState(weapon=ws))
        assert bs.monster_weapon_name == "Rapier"
        assert bs.monster_weapon_damage_die == 8
        assert "finesse" in bs.monster_weapon_properties
