"""Tests for the UI-facing features: area map, inventory use/stacking/comparison,
ability summaries, XP display and the character creation previews."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytest.importorskip("httpx")

import web.game_session as game_session
from engine.abilities import summarize_ability
from web.routes.game import build_area_map
from test_web_flow import client, load, patch, goto  # noqa: F401  (client is a fixture)

CAMPAIGN = game_session.get_campaign()
ABILITIES = game_session.get_abilities()
POTION = {"name": "Healing Potion", "description": "", "type": "potion", "healing_amount": 20}


def _all_locations():
    return [loc for act in CAMPAIGN["acts"] for loc in act["locations"]]


class TestAreaMap:
    @pytest.mark.parametrize("location", _all_locations(), ids=lambda loc: loc["name"])
    def test_every_area_is_placed_inside_the_map(self, location):
        area_map = build_area_map(location, location["areas"][0], [])
        assert {n["id"] for n in area_map["nodes"]} == {a["id"] for a in location["areas"]}
        for node in area_map["nodes"]:
            assert 0 < node["x"] < 100 and 0 < node["y"] < 100
        positions = [(n["x"], n["y"]) for n in area_map["nodes"]]
        assert len(set(positions)) == len(positions)

    def test_entry_is_on_top_and_neighbours_are_reachable(self):
        town = CAMPAIGN["acts"][0]["locations"][0]
        area_map = build_area_map(town, town["areas"][0], [])
        nodes = {n["id"]: n for n in area_map["nodes"]}
        assert nodes["town_square"]["current"]
        assert nodes["town_square"]["y"] == min(n["y"] for n in nodes.values())
        assert {i for i, n in nodes.items() if n["reachable"]} == set(town["areas"][0]["connections"])
        assert nodes["market"]["shop"] and nodes["tavern"]["rest"]
        assert nodes["town_square"]["danger"] == "safe"

    def test_each_connection_is_drawn_once(self):
        town = CAMPAIGN["acts"][0]["locations"][0]
        edges = build_area_map(town, town["areas"][0], [])["edges"]
        pairs = [frozenset((e["a"], e["b"])) for e in edges]
        assert len(pairs) == len(set(pairs)) == 6

    def test_boss_marker_turns_into_cleared(self):
        woods = CAMPAIGN["acts"][0]["locations"][1]
        grove = lambda defeated: next(  # noqa: E731
            n for n in build_area_map(woods, woods["areas"][0], defeated)["nodes"] if n["id"] == "grove")
        assert grove([])["boss"] and not grove([])["boss_defeated"]
        assert grove(["Shard Guardian"])["boss_defeated"] and not grove(["Shard Guardian"])["boss"]

    def test_location_page_moves_through_the_map(self, client):
        page = client.get("/game").text
        assert "area-map" in page and "You are here" in page
        assert client.post("/game/move", data={"area_id": "market"}).status_code == 200
        assert load(client)["area_id"] == "market"


class TestInventory:
    def test_drinking_a_potion_heals_and_consumes_it(self, client):
        patch(client, char_inventory=[POTION, POTION], char_current_hit_points=1)
        page = client.post("/inventory/use", data={"item_index": 0}).text
        char = load(client)["character"]
        assert char["current_hit_points"] == min(char["max_hit_points"], 21)
        assert len(char["inventory"]) == 1
        assert "recover" in page

    def test_potion_is_kept_at_full_health(self, client):
        patch(client, char_inventory=[POTION])
        page = client.post("/inventory/use", data={"item_index": 0}).text
        assert len(load(client)["character"]["inventory"]) == 1
        assert "already at full health" in page

    def test_only_potions_can_be_used(self, client):
        patch(client, char_inventory=[{"name": "Dagger", "type": "weapon"}], char_current_hit_points=1)
        client.post("/inventory/use", data={"item_index": 0})
        client.post("/inventory/use", data={"item_index": 7})
        char = load(client)["character"]
        assert char["current_hit_points"] == 1 and len(char["inventory"]) == 1

    def test_identical_potions_are_stacked(self, client):
        patch(client, char_inventory=[POTION, POTION, POTION])
        page = client.get("/inventory").text
        assert page.count('action="/inventory/use"') == 1
        assert "&times;3" in page

    def test_gear_is_compared_with_what_is_equipped(self, client):
        patch(client, char_inventory=[
            {"name": "Greatsword", "type": "weapon"}, {"name": "Dagger", "type": "weapon"},
            {"name": "Leather", "type": "armor"}])
        page = client.get("/inventory").text
        assert "+2.5 avg damage vs equipped" in page      # 2d6 against the Longsword's 1d8
        assert "-2 avg damage vs equipped" in page
        assert "compare-worse" in page and "AC vs equipped" in page
        # Previewing armor must not change what is worn
        assert load(client)["character"]["armor"] == "Chain Mail"


class TestAbilitySummary:
    def test_damage_scales_with_level(self):
        strike = ABILITIES["power_strike"]
        assert summarize_ability(strike, 1) == ["1d8 + mod slashing"]
        assert summarize_ability(strike, 5) == ["2d8 + mod slashing"]

    def test_heal_and_effects_are_listed(self):
        assert summarize_ability(ABILITIES["second_wind"], 1) == ["Heal 1d10 + level"]
        assert summarize_ability(ABILITIES["rallying_cry"], 4) == [
            "Heal 1d6 + mod", "Self: damage bonus +2, whole fight"]

    @pytest.mark.parametrize("ability_id", sorted(ABILITIES))
    def test_every_ability_has_a_summary(self, ability_id):
        assert summarize_ability(ABILITIES[ability_id], 20)


class TestBattleScreen:
    def test_abilities_and_stacked_items_have_hotkeys(self, client):
        patch(client, char_inventory=[POTION, POTION])
        goto(client, 1, "Whispering Woods", "clearing")
        page = client.get("/battle/start").text
        assert 'data-hotkey="a"' in page and 'data-hotkey="1"' in page
        assert "1d8 + mod slashing" in page
        assert page.count('action="/battle/item"') == 1 and 'data-hotkey="q"' in page
        assert 'data-combatant="monster"' in page

    def test_victory_rewards_survive_a_refresh(self, client):
        goto(client, 1, "Whispering Woods", "clearing")
        patch(client, char_current_hit_points=10_000, char_max_hit_points=10_000)
        client.get("/battle/start")
        data = load(client)
        data["battle"]["monster"]["hp"] = 1
        patch(client, battle=data["battle"])
        for _ in range(60):
            response = client.post("/battle/attack")
            if response.url.path != "/battle/":
                break
        assert "Rewards" in response.text
        assert "Rewards" in client.get("/battle/victory").text
        assert "xp-bar" in response.text


class TestCharacterCreation:
    def test_class_cards_show_playstyle_and_abilities(self, client):
        client.get("/character/new")
        page = client.post("/character/race", data={"race": "Human"}).text
        for class_name, props in game_session.get_classes().items():
            assert props["playstyle"] in page
        assert "Power Strike" in page and "Champion" in page

    def test_details_preview_shows_final_numbers(self, client):
        client.get("/character/new")
        client.post("/character/race", data={"race": "Human"})
        page = client.post("/character/class", data={"class_name": "Monk"}).text
        assert "char-preview" in page and "power points" in page
        # Monk's Unarmored Defense is part of the previewed AC
        assert 'id="preview-ac"' in page
        client.post("/character/create", data={"name": "Preview", "weapon": "Quarterstaff", "armor": ""})
        created_ac = load(client)["character"]["armor_class"]
        assert f'data-default="{created_ac}"' in page
