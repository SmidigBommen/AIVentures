"""Tests for the save/load manager."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from web.game_session import GameSession, BattleState, CharacterCreationState, get_campaign
from characterFactory import CharacterFactory
from weaponFactory import WeaponFactory
from armorFactory import ArmorFactory
from items import HealingPotion, QuestItem
from character import WeaponSlot
from web import save_manager


def _make_session():
    """Create a GameSession with a character for testing."""
    session = GameSession("test-session-id")
    factory = CharacterFactory()
    char = factory.create_character("SaveHero", "Dwarf", "Fighter")

    wf = WeaponFactory()
    char.equip_weapon(wf.get_weapon_by_name("Longsword"), WeaponSlot.MAIN_HAND)

    af = ArmorFactory()
    char.equip(af.get_armor_by_name("Chain Mail"))

    char.level = 4
    char.xp = 200
    char.gold = 100
    char.current_hit_points = 30
    char.max_hit_points = 40
    char.add_skill_proficiency("Athletics")
    char.add_item(HealingPotion("Minor Healing Potion", 5))
    char.add_item(QuestItem("Goblin Ear", "A severed ear", "quest_goblin"))

    session.character = char
    session.character_creation = CharacterCreationState(
        race="Dwarf", class_name="Fighter", name="SaveHero",
        weapon="Longsword", armor="Chain Mail",
        portrait="/static/images/player_fighter.png",
        skills=["Athletics"],
    )

    campaign = get_campaign()
    session.act = campaign["acts"][0]
    session.current_location = session.act["locations"][0]
    session.current_area = session.current_location["areas"][0]

    session.active_quests = {"q1": {"progress": 3, "status": "active"}}
    session.completed_quests = ["q0"]
    session.monster_kills = 12

    session.set_flash("test_msg", "hello")
    session.battle_rewards = {"xp": 100}

    return session


@pytest.fixture(autouse=True)
def use_tmp_saves_dir(tmp_path, monkeypatch):
    """Redirect save_manager to use a temp directory for all tests."""
    monkeypatch.setattr(save_manager, "SAVES_DIR", tmp_path)


class TestCreateAndList:
    def test_create_save(self):
        session = _make_session()
        result = save_manager.create_save(session)

        assert "save_id" in result
        assert result["metadata"]["character_name"] == "SaveHero"
        assert result["metadata"]["character_level"] == 4
        assert result["metadata"]["character_class"] == "Fighter"
        assert result["metadata"]["character_race"] == "Dwarf"
        assert result["metadata"]["monster_kills"] == 12
        assert result["metadata"]["portrait"] == "/static/images/player_fighter.png"

    def test_list_saves_returns_created(self):
        session = _make_session()
        save_manager.create_save(session)
        save_manager.create_save(session)

        saves = save_manager.list_saves()
        assert len(saves) == 2
        assert all(s["metadata"]["character_name"] == "SaveHero" for s in saves)

    def test_list_saves_sorted_newest_first(self):
        s1 = _make_session()
        s1.character.gold = 10
        save_manager.create_save(s1)

        s2 = _make_session()
        s2.character.gold = 99
        save_manager.create_save(s2)

        saves = save_manager.list_saves()
        assert len(saves) == 2
        # Most recent is first
        assert saves[0]["updated_at"] >= saves[1]["updated_at"]

    def test_list_saves_empty(self):
        assert save_manager.list_saves() == []


class TestLoadSave:
    def test_load_roundtrip(self):
        session = _make_session()
        created = save_manager.create_save(session)

        loaded = save_manager.load_save(created["save_id"])
        assert loaded is not None
        assert loaded.character.name == "SaveHero"
        assert loaded.character.level == 4
        assert loaded.character.gold == 100
        assert loaded.character.current_hit_points == 30
        assert loaded.monster_kills == 12
        assert loaded.active_quests == {"q1": {"progress": 3, "status": "active"}}
        assert loaded.completed_quests == ["q0"]

    def test_load_gets_fresh_session_id(self):
        session = _make_session()
        created = save_manager.create_save(session)
        loaded = save_manager.load_save(created["save_id"])
        assert loaded.session_id != "test-session-id"

    def test_load_nonexistent_returns_none(self):
        assert save_manager.load_save("nonexistent-id") is None

    def test_location_restored(self):
        session = _make_session()
        created = save_manager.create_save(session)
        loaded = save_manager.load_save(created["save_id"])
        assert loaded.current_location is not None
        assert loaded.current_location["name"] == session.current_location["name"]
        assert loaded.current_area["id"] == session.current_area["id"]

    def test_inventory_preserved(self):
        session = _make_session()
        created = save_manager.create_save(session)
        loaded = save_manager.load_save(created["save_id"])
        types = [type(item).__name__ for item in loaded.character.inventory]
        assert "HealingPotion" in types
        assert "QuestItem" in types


class TestOverwriteSave:
    def test_overwrite_updates_data(self):
        session = _make_session()
        created = save_manager.create_save(session)

        session.character.gold = 999
        session.character.level = 7
        save_manager.overwrite_save(created["save_id"], session)

        loaded = save_manager.load_save(created["save_id"])
        assert loaded.character.gold == 999
        assert loaded.character.level == 7

    def test_overwrite_preserves_created_at(self):
        session = _make_session()
        created = save_manager.create_save(session)
        original_created = created["created_at"]

        result = save_manager.overwrite_save(created["save_id"], session)
        assert result["created_at"] == original_created

    def test_overwrite_nonexistent_returns_none(self):
        session = _make_session()
        assert save_manager.overwrite_save("no-such-id", session) is None


class TestDeleteSave:
    def test_delete_removes_file(self):
        session = _make_session()
        created = save_manager.create_save(session)
        assert save_manager.get_save_count() == 1

        deleted = save_manager.delete_save(created["save_id"])
        assert deleted is True
        assert save_manager.get_save_count() == 0

    def test_delete_nonexistent_returns_false(self):
        assert save_manager.delete_save("no-such-id") is False


class TestSaveCount:
    def test_count_empty(self):
        assert save_manager.get_save_count() == 0

    def test_count_after_creates(self):
        session = _make_session()
        save_manager.create_save(session)
        save_manager.create_save(session)
        save_manager.create_save(session)
        assert save_manager.get_save_count() == 3


class TestEphemeralFieldsCleared:
    def test_flash_cleared_in_save(self):
        session = _make_session()
        assert session.pop_flash("test_msg") == "hello"

        session.set_flash("test_msg", "hello again")
        created = save_manager.create_save(session)

        # Read raw file to check _flash is empty
        path = save_manager._save_file(created["save_id"])
        with open(path) as f:
            raw = json.load(f)
        assert raw["session_data"]["_flash"] == {}
        assert raw["session_data"]["battle_rewards"] is None


class TestGetSaveMetadata:
    def test_returns_metadata(self):
        session = _make_session()
        created = save_manager.create_save(session)
        meta = save_manager.get_save_metadata(created["save_id"])
        assert meta is not None
        assert meta["save_id"] == created["save_id"]
        assert meta["metadata"]["character_name"] == "SaveHero"

    def test_nonexistent_returns_none(self):
        assert save_manager.get_save_metadata("nope") is None
