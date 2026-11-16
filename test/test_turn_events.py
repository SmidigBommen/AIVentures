"""Tests for the structured turn events that drive the battle stage playback."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytest.importorskip("httpx")

import web.game_session as game_session
from dice import Dice
from engine.turn_events import FX_KEYS, TurnRecorder, ability_fx, outcome_of
from test_web_flow import client, load, patch, goto  # noqa: F401  (client is a fixture)

ABILITIES = game_session.get_abilities()
MONSTER_ABILITIES = game_session.get_monster_abilities()["abilities"]
SPRITES = game_session.get_battle_sprites()
STATIC = Path(__file__).parent.parent / "web"


class TestRecorder:
    def test_hp_changes_are_measured_between_steps(self):
        rec = TurnRecorder(player_hp=20, monster_hp=30)
        rec.add("player", "attack", 20, 23, name="Longsword", outcome="hit", fx="slashing")
        rec.add("monster", "ability", 14, 26, name="Life Drain", outcome="hit", fx="necrotic")
        assert [(e["player"], e["monster"]) for e in rec.events] == [(0, -7), (-6, 3)]
        assert rec.events[0]["ranged"] is False

    def test_unknown_effect_falls_back_to_impact(self):
        rec = TurnRecorder(10, 10)
        assert rec.add("player", "attack", 10, 10, fx="glitter")["fx"] == "impact"

    def test_outcome(self):
        assert outcome_of(True, crit=True) == "crit"
        assert outcome_of(True) == "hit"
        assert outcome_of(False, half=True) == "half"
        assert outcome_of(False) == "miss"

    @pytest.mark.parametrize("ability_id", sorted(ABILITIES))
    def test_every_player_ability_has_a_known_effect(self, ability_id):
        assert ability_fx(ABILITIES[ability_id]) in FX_KEYS

    @pytest.mark.parametrize("ability_id", sorted(MONSTER_ABILITIES))
    def test_every_monster_ability_has_a_known_effect(self, ability_id):
        assert ability_fx(MONSTER_ABILITIES[ability_id]) in FX_KEYS

    def test_effect_choice(self):
        assert ability_fx(ABILITIES["fireball"]) == "fire"
        assert ability_fx(ABILITIES["second_wind"]) == "heal"
        assert ability_fx(ABILITIES["arcane_shield"]) == "shield"
        assert ability_fx(MONSTER_ABILITIES["war_cry"]) == "buff"
        assert ability_fx(MONSTER_ABILITIES["blight_spores"]) == "poison"


def _start(client, hp=500):
    goto(client, 1, "Whispering Woods", "clearing")
    # Tough enough to survive anything, including an opening blow before the first turn
    patch(client, char_current_hit_points=10_000, char_max_hit_points=10_000)
    client.get("/battle/start")
    data = load(client)
    data["battle"]["monster"].update(hp=hp, max_hp=hp)
    patch(client, battle=data["battle"])


def _turn(client):
    battle = load(client)["battle"]
    return battle["turn_seq"], battle["turn_events"]


class TestTurnEventsThroughRoutes:
    def test_attack_records_player_then_monster(self, client, monkeypatch):
        _start(client)
        seq_before, _ = _turn(client)
        monkeypatch.setattr(Dice, "roll_d20", staticmethod(lambda: 15))
        hp_before = load(client)["battle"]["monster"]["hp"]
        client.post("/battle/attack")
        seq, events = _turn(client)
        assert seq == seq_before + 1
        first = events[0]
        assert (first["actor"], first["kind"], first["name"]) == ("player", "attack", "Longsword")
        assert first["outcome"] == "hit" and first["fx"] == "slashing" and first["monster"] < 0
        assert events[1]["actor"] == "monster"
        # The deltas add up to the real HP change
        assert hp_before + sum(e["monster"] for e in events) == load(client)["battle"]["monster"]["hp"]

    def test_natural_20_is_a_crit_and_natural_1_a_miss(self, client, monkeypatch):
        _start(client)
        monkeypatch.setattr(Dice, "roll_d20", staticmethod(lambda: 20))
        client.post("/battle/attack")
        assert _turn(client)[1][0]["outcome"] == "crit"
        monkeypatch.setattr(Dice, "roll_d20", staticmethod(lambda: 1))
        client.post("/battle/attack")
        events = _turn(client)[1]
        assert events[0]["outcome"] == "miss" and events[0]["monster"] == 0

    def test_defend_item_and_ability(self, client):
        _start(client)
        client.post("/battle/defend")
        assert _turn(client)[1][0]["kind"] == "defend"

        potion = {"name": "Healing Potion", "description": "", "type": "potion", "healing_amount": 20}
        patch(client, char_inventory=[potion], char_current_hit_points=100)
        client.post("/battle/item", data={"item_index": 0})
        item = _turn(client)[1][0]
        assert (item["kind"], item["fx"], item["player"]) == ("item", "heal", 20)

        patch(client, char_power_points=5, char_current_hit_points=100)
        client.post("/battle/ability", data={"ability_id": "second_wind"})
        ability = _turn(client)[1][0]
        assert (ability["kind"], ability["name"], ability["outcome"]) == ("ability", "Second Wind", None)
        assert ability["fx"] == "heal" and ability["player"] > 0

    def test_rejected_actions_do_not_start_a_turn(self, client):
        _start(client)
        seq = _turn(client)[0]
        patch(client, char_power_points=0)
        client.post("/battle/ability", data={"ability_id": "action_surge"})
        client.post("/battle/item", data={"item_index": 99})
        assert _turn(client)[0] == seq

    def test_ranged_weapon_does_not_lunge(self, client, monkeypatch):
        _start(client)
        creation = load(client)["character_creation"]
        creation["weapon"] = "Longbow"
        patch(client, character_creation=creation)
        monkeypatch.setattr(Dice, "roll_d20", staticmethod(lambda: 15))
        client.post("/battle/attack")
        first = _turn(client)[1][0]
        assert first["name"] == "Longbow"
        assert first["ranged"] and first["fx"] == "piercing"

    def test_poison_tick_is_a_condition_event(self, client):
        _start(client)
        data = load(client)
        data["battle"]["monster"]["effects"] = [
            {"stat": "poison", "value": 4, "duration": 3, "source": "Test"}]
        patch(client, battle=data["battle"])
        client.post("/battle/defend")
        conditions = [e for e in _turn(client)[1] if e["kind"] == "condition"]
        assert conditions and conditions[0]["actor"] == "monster"
        assert conditions[0]["fx"] == "poison" and conditions[0]["monster"] == -4

    def test_stage_carries_the_turn_and_final_blow_reaches_victory(self, client):
        _start(client, hp=1)
        page = client.get("/battle").text
        assert "battle-stage" in page and "data-turn-events" in page
        assert 'src="/static/js/battle.js"' in page
        for _ in range(60):
            response = client.post("/battle/attack")
            if response.url.path != "/battle/":
                break
        assert 'data-finale="victory"' in response.text
        assert "&#34;kind&#34;: &#34;attack&#34;" in response.text or '"kind": "attack"' in response.text

    def test_old_session_without_turn_fields_loads(self, client):
        _start(client)
        data = load(client)
        del data["battle"]["turn_events"], data["battle"]["turn_seq"]
        patch(client, battle=data["battle"])
        assert client.get("/battle").status_code == 200


def _sheets():
    groups = [SPRITES["players"], SPRITES["monsters"], SPRITES["bosses"]]
    return [entry for group in groups for entry in group.values()] + [
        SPRITES["default_player"], SPRITES["default_monster"]]


class TestSprites:
    def test_mapped_sheets_exist_with_the_shared_layout(self):
        Image = pytest.importorskip("PIL.Image")
        for entry in _sheets():
            with Image.open(STATIC / entry["sheet"].lstrip("/")) as img:
                assert img.size == (256, 192), entry       # 4x4 frames of 64x48
            assert 1 <= entry["scale"] <= 1.6

    def test_every_race_and_boss_has_a_sprite(self):
        races = set()
        for act in game_session.get_campaign()["acts"]:
            for location in act["locations"]:
                for area in location["areas"]:
                    races.update(area.get("monster_types", []))
        assert races <= set(SPRITES["monsters"])
        assert set(game_session.get_bosses()) == set(SPRITES["bosses"])

    def test_stage_shows_sprites_for_both_sides(self, client):
        _start(client)
        data = load(client)
        data["battle"]["monster"]["race"] = "Troll"
        data["character_creation"]["portrait"] = "/static/images/player_wizard.png"
        patch(client, battle=data["battle"], character_creation=data["character_creation"])
        page = client.get("/battle").text
        assert 'data-sheet="/static/images/sprites/troll.png"' in page
        assert 'data-sheet="/static/images/sprites/wizard.png"' in page
        assert "actor-portrait" not in page

    def test_unknown_race_and_portrait_use_the_default_sprites(self, client):
        _start(client)
        data = load(client)
        data["battle"]["monster"]["race"] = "Gelatinous Cube"
        data["character_creation"]["portrait"] = ""
        patch(client, battle=data["battle"], character_creation=data["character_creation"])
        page = client.get("/battle").text
        assert 'data-sheet="/static/images/sprites/orc.png"' in page
        assert 'data-sheet="/static/images/sprites/knight.png"' in page

    def test_boss_fight_uses_the_boss_sprite(self, client):
        goto(client, 1, "Whispering Woods", "clearing")
        boss_id = next(iter(SPRITES["bosses"]))
        _start(client)
        data = load(client)
        data["battle"]["monster"].update(is_boss=True, boss_id=boss_id)
        patch(client, battle=data["battle"])
        page = client.get("/battle").text
        assert SPRITES["bosses"][boss_id]["sheet"] in page
