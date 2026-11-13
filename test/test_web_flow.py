"""End-to-end tests through the FastAPI routes: bosses, flee, events, act travel.

These drive the real app with a test client, so they cover the wiring between
routes, session persistence, the engine and the templates.
"""

import sys
import json
import random
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from dice import Dice
import web.game_session as game_session
from web.app import app
from web.routes import game as game_routes
from engine import campaign as rules

CAMPAIGN = game_session.get_campaign()
ACT1, ACT2, ACT3 = CAMPAIGN["acts"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A client with a freshly created Fighter, with sessions stored in a temp dir."""
    monkeypatch.setattr(game_session, "SESSIONS_DIR", tmp_path)
    orig_d20, orig_roll = Dice.roll_d20, Dice.roll
    with TestClient(app) as c:
        c.post("/character/race", data={"race": "Human"})
        c.post("/character/class", data={"class_name": "Fighter"})
        response = c.post("/character/create", data={
            "name": "Tester", "weapon": "Longsword", "armor": "Chain Mail",
            "skills": ["Athletics", "Perception"]})
        assert response.status_code == 200
        c.sessions_dir = tmp_path
        yield c
    Dice.roll_d20, Dice.roll = orig_d20, orig_roll


def _session_path(client) -> Path:
    files = list(client.sessions_dir.glob("*.json"))
    assert len(files) == 1
    return files[0]


def load(client) -> dict:
    return json.loads(_session_path(client).read_text(encoding="utf-8"))


def patch(client, **changes):
    """Edit the stored session directly (character sub-dict via char_*)."""
    data = load(client)
    for key, value in changes.items():
        if key.startswith("char_"):
            data["character"][key[5:]] = value
        else:
            data[key] = value
    _session_path(client).write_text(json.dumps(data), encoding="utf-8")


def goto(client, act_num, location_name, area_id):
    patch(client, act_num=act_num, location_name=location_name, area_id=area_id)


def make_strong(client):
    patch(client, char_level=20, char_max_hit_points=9999, char_current_hit_points=9999)


def fight_until_over(client, max_rounds=300):
    """Attack until the battle ends. Every d20 is a 20 so the fight is short and deterministic
    in outcome (callers pair this with make_strong so the player survives the return crits)."""
    Dice.roll_d20 = lambda: 20
    for _ in range(max_rounds):
        response = client.post("/battle/attack", follow_redirects=False)
        if response.headers["location"] != "/battle":
            return response.headers["location"]
    raise AssertionError("battle did not end")


class TestLocationPage:
    def test_renders_with_act_title(self, client):
        page = client.get("/game")
        assert page.status_code == 200
        assert "The Awakening" in page.text

    def test_boss_panel_only_in_boss_area(self, client):
        assert "Confront" not in client.get("/game").text
        goto(client, 1, "Whispering Woods", "grove")
        page = client.get("/game").text
        assert "Confront The Shard Guardian" in page

    def test_dead_character_is_sent_to_defeat_screen(self, client):
        patch(client, char_current_hit_points=0)
        response = client.get("/game/", follow_redirects=False)
        assert response.headers["location"] == "/battle/defeat"


class TestBossBattle:
    def test_cannot_start_boss_outside_boss_area(self, client):
        response = client.post("/battle/boss", follow_redirects=False)
        assert response.headers["location"] == "/game"
        assert load(client)["battle"]["is_active"] is False

    def test_boss_fight_to_victory_unlocks_progress(self, client):
        make_strong(client)
        goto(client, 1, "Whispering Woods", "grove")
        client.post("/battle/boss")
        data = load(client)
        assert data["battle"]["is_active"] is True
        assert data["battle"]["monster"]["boss_id"] == "Shard Guardian"

        arena = client.get("/battle")
        assert arena.status_code == 200
        assert "Boss Battle" in arena.text
        assert "/battle/flee" not in arena.text

        assert fight_until_over(client) == "/battle/victory"
        data = load(client)
        assert data["defeated_bosses"] == ["Shard Guardian"]

        victory = client.get("/battle/victory")
        assert "Shard of Verdance recovered" in victory.text
        # Boss is gone from the area afterwards
        assert "Confront" not in client.get("/game").text

    def test_boss_cannot_be_fled(self, client):
        make_strong(client)
        goto(client, 1, "Whispering Woods", "grove")
        client.post("/battle/boss")
        Dice.roll_d20 = lambda: 20
        client.post("/battle/flee")
        assert load(client)["battle"]["is_active"] is True

    def test_boss_enrages_at_half_health(self, client):
        make_strong(client)
        goto(client, 1, "Whispering Woods", "grove")
        client.post("/battle/boss")
        data = load(client)
        data["battle"]["monster"]["hp"] = data["battle"]["monster"]["max_hp"] // 2
        _session_path(client).write_text(json.dumps(data))
        client.post("/battle/defend")
        data = load(client)
        assert data["battle"]["monster"]["enraged"] is True
        assert "Enraged" in client.get("/battle").text

    def test_final_boss_is_sealed_until_lieutenant_falls(self, client):
        make_strong(client)
        defeated = rules.act_boss_ids(ACT1) + rules.act_boss_ids(ACT2)
        patch(client, defeated_bosses=defeated)
        goto(client, 3, "The Convergence", "ritual_chamber")
        assert "Sealed" in client.get("/game").text
        client.post("/battle/boss")
        assert load(client)["battle"]["is_active"] is False

        patch(client, defeated_bosses=defeated + ["Lady Vex (Final Battle)"])
        client.post("/battle/boss")
        assert load(client)["battle"]["monster"]["boss_id"] == "Malachar the Void-touched"

        assert fight_until_over(client) == "/battle/victory"
        assert "Witness the Ending" in client.get("/battle/victory").text
        ending = client.get("/game/ending")
        assert ending.status_code == 200
        assert "The Crown Restored" in ending.text

    def test_ending_is_locked_until_campaign_complete(self, client):
        response = client.get("/game/ending", follow_redirects=False)
        assert response.headers["location"] == "/game"

    def test_losing_to_a_boss_leaves_it_undefeated(self, client):
        patch(client, char_current_hit_points=1, char_max_hit_points=1)
        goto(client, 1, "Whispering Woods", "grove")
        client.post("/battle/boss")
        if load(client)["battle"]["is_active"]:
            Dice.roll_d20 = lambda: 2   # the player whiffs; the boss' save DCs always land
            location = None
            for _ in range(200):
                location = client.post("/battle/defend", follow_redirects=False).headers["location"]
                if location != "/battle":
                    break
            assert location == "/battle/defeat"
        assert load(client)["defeated_bosses"] == []
        assert client.get("/battle/defeat").status_code == 200


class TestRandomBattle:
    def _start(self, client):
        goto(client, 1, "Whispering Woods", "entrance")
        client.get("/battle/start")
        assert load(client)["battle"]["is_active"] is True

    def test_no_battle_where_no_monsters_live(self, client):
        response = client.get("/battle/start", follow_redirects=False)   # Town Square
        assert response.headers["location"] == "/game"

    def test_start_does_not_restart_an_active_battle(self, client):
        make_strong(client)
        self._start(client)
        name = load(client)["battle"]["monster"]["name"]
        patch_data = load(client)
        patch_data["battle"]["round_count"] = 7
        _session_path(client).write_text(json.dumps(patch_data))
        client.get("/battle/start")
        assert load(client)["battle"]["round_count"] == 7
        assert load(client)["battle"]["monster"]["name"] == name

    def test_monster_gets_racial_abilities(self, client):
        make_strong(client)
        self._start(client)
        assert load(client)["battle"]["monster"]["abilities"] == ["dirty_trick"]

    def test_successful_flee_ends_battle(self, client):
        make_strong(client)
        self._start(client)
        Dice.roll_d20 = lambda: 20
        response = client.post("/battle/flee", follow_redirects=False)
        assert response.headers["location"] == "/game"
        assert load(client)["battle"]["is_active"] is False
        assert "slip away" in client.get("/game").text

    def test_failed_flee_costs_the_turn(self, client):
        make_strong(client)
        self._start(client)
        round_before = load(client)["battle"]["round_count"]
        Dice.roll_d20 = lambda: 1
        client.post("/battle/flee")
        data = load(client)
        assert data["battle"]["is_active"] is True
        assert data["battle"]["round_count"] == round_before + 1

    def test_defend_bonus_expires_at_end_of_round(self, client):
        make_strong(client)
        self._start(client)
        ac_before = load(client)["character"]["armor_class"]
        client.post("/battle/defend")
        data = load(client)
        assert data["character"]["armor_class"] == ac_before
        assert not any(e["source"] == "Defend" for e in data["battle"]["player_effects"])

    def test_invalid_item_does_not_cost_a_turn(self, client):
        make_strong(client)
        self._start(client)
        round_before = load(client)["battle"]["round_count"]
        client.post("/battle/item", data={"item_index": 99})
        assert load(client)["battle"]["round_count"] == round_before

    def test_full_fight_and_victory_screen(self, client):
        make_strong(client)
        self._start(client)
        assert fight_until_over(client) == "/battle/victory"
        assert client.get("/battle/victory").status_code == 200
        assert load(client)["monster_kills"] == 1

    def test_every_class_ability_works_through_the_route(self, client):
        make_strong(client)
        patch(client, char_power_points=99)
        self._start(client)
        for ability_id in ("power_strike", "second_wind", "action_surge", "rallying_cry", "champions_blow"):
            if not load(client)["battle"]["is_active"]:
                client.get("/battle/victory")
                client.get("/battle/start")
            response = client.post("/battle/ability", data={"ability_id": ability_id})
            assert response.status_code == 200

    def test_poison_kills_monster_at_end_of_round(self, client):
        make_strong(client)
        self._start(client)
        data = load(client)
        data["battle"]["monster"]["hp"] = 2
        data["battle"]["monster"]["effects"] = [
            {"stat": "poison", "value": 5, "duration": 3, "source": "test"},
            {"stat": "stun", "value": 1, "duration": 1, "source": "test"}]
        _session_path(client).write_text(json.dumps(data))
        response = client.post("/battle/defend", follow_redirects=False)
        assert response.headers["location"] == "/battle/victory"

    def test_stunned_player_loses_a_turn(self, client):
        make_strong(client)
        self._start(client)
        data = load(client)
        # Duration 2: survives this round's tick, costs the next turn, then expires
        data["battle"]["player_effects"] = [{"stat": "stun", "value": 1, "duration": 2, "source": "test"}]
        round_before = data["battle"]["round_count"]
        _session_path(client).write_text(json.dumps(data))
        client.post("/battle/defend")
        data = load(client)
        assert data["battle"]["round_count"] == round_before + 2
        assert data["battle"]["player_effects"] == []
        assert any("stunned" in line for line in data["battle"]["battle_log"])


class TestEvents:
    def test_event_flow(self, client, monkeypatch):
        monkeypatch.setattr(game_routes, "EVENT_CHANCE", 1.0)
        random.seed(5)
        client.post("/game/explore")           # Town Square: no monsters, so always an event
        data = load(client)
        event_id = data["pending_event"]
        assert event_id

        # The world view funnels to the pending event
        response = client.get("/game/", follow_redirects=False)
        assert response.headers["location"] == "/game/event"
        page = client.get("/game/event")
        assert page.status_code == 200
        assert game_session.get_events()[event_id]["title"] in page.text

        Dice.roll_d20 = lambda: 20
        client.post("/game/event/choose", data={"choice": 0})
        data = load(client)
        assert data["pending_event"] is None
        assert data["event_result"]["success"] is True
        assert data["events_resolved"] == 1
        assert "SUCCESS" in client.get("/game/event").text or "NAT 20" in client.get("/game/event").text

        response = client.post("/game/event/continue", follow_redirects=False)
        assert response.headers["location"] == "/game"
        assert load(client)["event_result"] is None
        assert client.get("/game").status_code == 200

    def test_special_event_is_one_time(self, client, monkeypatch):
        monkeypatch.setattr(game_routes, "EVENT_CHANCE", 1.0)
        monkeypatch.setattr(random, "random", lambda: 0.999)   # never an encounter
        goto(client, 1, "Rivermeet Town", "bridge")
        monkeypatch.setattr(game_routes, "EVENT_CHANCE", 1.1)
        client.post("/game/explore")
        assert load(client)["pending_event"] == "bridge_runes"
        client.post("/game/event/choose", data={"choice": 0})
        assert "bridge_runes" in load(client)["completed_events"]
        client.post("/game/event/continue")
        client.post("/game/explore")
        assert load(client)["pending_event"] != "bridge_runes"

    def test_invalid_choice_keeps_event_pending(self, client):
        patch(client, pending_event="abandoned_chest")
        client.post("/game/event/choose", data={"choice": 42})
        assert load(client)["pending_event"] == "abandoned_chest"

    def test_event_xp_can_level_up(self, client):
        patch(client, pending_event="bridge_runes", char_xp=149)
        Dice.roll_d20 = lambda: 20
        client.post("/game/event/choose", data={"choice": 0})
        data = load(client)
        assert data["character"]["level"] == 2
        assert data["event_result"]["leveled_up"] is True

    def test_battle_outcome_leads_to_a_fight(self, client):
        goto(client, 1, "Whispering Woods", "entrance")
        patch(client, pending_event="strange_tracks")
        Dice.roll_d20 = lambda: 1
        client.post("/game/event/choose", data={"choice": 0})
        assert load(client)["event_result"]["battle"] is True
        response = client.post("/game/event/continue", follow_redirects=False)
        assert response.headers["location"] == "/battle/start"


class TestTravelAndJournal:
    def test_travel_page_shows_locked_acts(self, client):
        page = client.get("/game/travel")
        assert page.status_code == 200
        assert "Whispering Woods" in page.text
        assert "Emberforge Mountains" not in page.text
        assert "Beyond the Horizon" in page.text

    def test_cannot_travel_to_locked_act(self, client):
        client.post("/game/travel", data={"location_name": "Emberforge Mountains"})
        assert load(client)["location_name"] == "Rivermeet Town"

    def test_travel_within_act_arrives_at_starting_area(self, client):
        client.post("/game/travel", data={"location_name": "Abandoned Watchtower"})
        data = load(client)
        assert data["location_name"] == "Abandoned Watchtower"
        assert data["area_id"] == "approach"

    def test_travel_to_unlocked_act_and_back(self, client):
        patch(client, defeated_bosses=rules.act_boss_ids(ACT1))
        assert "Emberforge Mountains" in client.get("/game/travel").text
        client.post("/game/travel", data={"location_name": "Emberforge Mountains"})
        data = load(client)
        assert (data["act_num"], data["location_name"]) == (2, "Emberforge Mountains")
        assert "Gathering the Fragments" in client.get("/game").text

        client.post("/game/travel", data={"location_name": "Rivermeet Town"})
        data = load(client)
        assert (data["act_num"], data["location_name"]) == (1, "Rivermeet Town")

    def test_lady_vex_ambushes_on_the_road(self, client):
        make_strong(client)
        defeated = rules.act_boss_ids(ACT1) + rules.act_boss_ids(ACT2)[:2]
        patch(client, defeated_bosses=defeated)
        goto(client, 2, "Emberforge Mountains", "mountain_pass")
        response = client.post(
            "/game/travel", data={"location_name": "Windswept Plains"}, follow_redirects=False)
        assert response.headers["location"] == "/battle"
        assert load(client)["battle"]["monster"]["boss_id"] == "Lady Vex"

        assert fight_until_over(client) == "/battle/victory"
        client.get("/battle/victory")
        # Once beaten she does not ambush again
        response = client.post(
            "/game/travel", data={"location_name": "The Crystalline Caves"}, follow_redirects=False)
        assert response.headers["location"] == "/game"

    def test_journal_renders_progress(self, client):
        page = client.get("/game/journal")
        assert page.status_code == 200
        assert "The Shard Guardian" in page.text
        assert "High Flamecaller" not in page.text      # Act 2 bosses stay hidden

        patch(client, defeated_bosses=["Shard Guardian"])
        assert "Shard of Verdance" in client.get("/game/journal").text


class TestSessionCompatibility:
    def test_session_without_new_fields_still_loads(self, client):
        """Saves from before this feature set must keep working."""
        data = load(client)
        for key in ("defeated_bosses", "pending_event", "event_result",
                    "completed_events", "events_resolved"):
            del data[key]
        for key in ("abilities", "cooldowns", "boss_id", "enraged", "con_mod", "wis_mod"):
            data["battle"]["monster"].pop(key, None)
        for item in data["character"]["inventory"]:
            item.pop("healing_amount", None)
        _session_path(client).write_text(json.dumps(data))

        assert client.get("/game").status_code == 200
        assert client.get("/game/journal").status_code == 200
        session = game_session.GameSession.from_dict(data)
        assert session.defeated_bosses == []
        assert session.battle.monster.abilities == []
        potions = {i.name: i.healing_amount for i in session.character.inventory}
        assert potions == {"Small Healing Potion": 10, "Medium Healing Potion": 25}

    def test_potion_healing_survives_roundtrip(self, client):
        data = load(client)
        data["character"]["inventory"].append(
            {"name": "Superior Healing Potion", "description": "", "type": "potion", "healing_amount": 50})
        _session_path(client).write_text(json.dumps(data))
        client.get("/game")   # load + flash-pop save is not guaranteed; force a save via travel
        client.post("/game/travel", data={"location_name": "Whispering Woods"})
        potions = {i["name"]: i["healing_amount"] for i in load(client)["character"]["inventory"]}
        assert potions["Superior Healing Potion"] == 50
        assert potions["Medium Healing Potion"] == 25

    def test_proficiency_is_restored_for_level(self, client):
        patch(client, char_level=8)
        session = game_session.GameSession.from_dict(load(client))
        assert session.character.proficiency_bonus == 3


class TestQuestTurnIn:
    def test_level_up_from_quest_grants_hp_and_power_points(self, client):
        patch(client, char_xp=140, char_current_hit_points=5, char_power_points=0,
              active_quests={"goblin_menace": {"progress": 5, "status": "ready"}})
        before = load(client)["character"]
        client.post("/shop/quest/turn-in", data={"quest_id": "goblin_menace"})
        after = load(client)["character"]
        assert after["level"] == 2
        assert after["max_hit_points"] > before["max_hit_points"]
        assert after["current_hit_points"] == 5 + (after["max_hit_points"] - before["max_hit_points"])
        assert after["power_points"] == after["max_power_points"] > 0
