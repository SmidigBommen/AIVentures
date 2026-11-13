import sys
import random
from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import (
    get_session, save_session, get_abilities, get_class_abilities, get_primary_modifier,
    get_quests, get_monster_taunts, get_monster_portraits, get_bosses, get_monster_abilities,
    get_save_modifiers, get_campaign, BATTLE_LOG_LIMIT,
)
from monsterFactory import MonsterFactory
from dice import Dice
from items import HealingPotion
from character import WeaponSlot
from lootGenerator import LootGenerator
from web.routes.shop import restock_shop
from engine.effects import (
    get_effect_bonus, tick_effects, is_stunned, resolve_round_conditions,
    describe_effect, CONDITION_LABELS, DOT_STATS,
)
from engine.combat import (
    get_weapon_attack_modifier, resolve_weapon_attack, resolve_flee,
    calculate_xp_reward, calculate_gold_reward,
)
from engine.abilities import resolve_player_ability
from engine.monster_ai import choose_monster_action, resolve_monster_ability, tick_cooldowns
from engine.leveling import grant_xp
from engine.quests import check_quest_progress
from engine.combatant import CombatantState
from engine import campaign as campaign_rules
from web.dependencies import require_character, require_battle

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_monster_taunt(race: str, context: str, boss_id: str = "") -> str:
    """Get a random taunt by race and context. Bosses speak their own lines."""
    if boss_id:
        lines = get_bosses().get(boss_id, {}).get("taunts", {}).get(context)
        if lines:
            return random.choice(lines)
    all_taunts = get_monster_taunts()
    default = all_taunts.get("Default", {})
    taunts = all_taunts.get(race, default)
    lines = taunts.get(context, default.get(context, [""]))
    return random.choice(lines)


def _taunt(battle, context: str) -> str:
    return get_monster_taunt(battle.monster.race, context, battle.monster.boss_id)


def get_monster_for_area(area, location=None):
    """Generate a monster appropriate for the area."""
    # Get monster info from area - default to Goblin for simple areas
    monster_types = area.get("monster_types", ["Goblin"])
    monster_race = random.choice(monster_types)

    # Get level range from location's encounterLevel field
    level_range_str = None
    if location:
        level_range_str = location.get("encounterLevel")
    if level_range_str and "-" in str(level_range_str):
        min_level, max_level = map(int, level_range_str.split("-"))
        level = random.randint(min_level, max_level)
    else:
        # Fall back to area encounter_levels or default
        level_range = area.get("encounter_levels", [1, 2])
        if isinstance(level_range, list) and len(level_range) >= 2:
            level = random.randint(level_range[0], level_range[1])
        else:
            level = 1

    return monster_race, level


def classify_log_entry(entry: str) -> str:
    """CSS class for a battle log line (drives color and sound)."""
    if "CRITICAL" in entry:
        return "crit"
    if '"' in entry and ":" in entry:
        return "taunt"
    if "hits for" in entry or "deals" in entry or "damage" in entry or "drains" in entry:
        return "damage"
    if "heals" in entry or "regenerates" in entry:
        return "heal"
    if "defensive stance" in entry:
        return "defend"
    if "misses" in entry or "Miss" in entry or "resist" in entry:
        return "miss"
    if "stunned" in entry or "afflicted" in entry or "flee" in entry:
        return "condition"
    if "uses" in entry or "casts" in entry:
        return "ability"
    return ""


def effect_badges(effects, friendly_is_positive=True):
    """Build display badges for a list of active effects."""
    badges = []
    for eff in effects:
        stat = eff["stat"]
        if stat in CONDITION_LABELS:
            label = CONDITION_LABELS[stat]
            harmful = stat != "regen"
        else:
            label = f"{stat.replace('_', ' ').title().replace('Ac', 'AC')} {eff['value']:+d}"
            harmful = eff["value"] < 0
        title = f"{eff['source']}: {describe_effect(eff)}"
        if eff["duration"] > 0:
            title += f" ({eff['duration']} rd)"
        badges.append({"label": label, "title": title, "kind": "debuff" if harmful else "buff"})
    return badges


def begin_battle(session, monster_state: CombatantState, intro_lines=None) -> bool:
    """Set up battle state and roll initiative.

    Returns False if the player was struck down by the opening blow.
    """
    char = session.character
    battle = session.battle
    battle.monster = monster_state
    battle.is_active = True
    battle.round_count = 1
    battle.battle_log = list(intro_lines or [])
    battle.player_effects = []

    player_init = char.dexterity_modifier + Dice.roll_d20()
    monster_init = monster_state.dex_mod + Dice.roll_d20()
    battle.initiative_order = sorted(
        [("player", player_init), ("monster", monster_init)], key=lambda x: x[1], reverse=True)
    battle.is_player_turn = battle.initiative_order[0][0] == "player"

    battle.battle_log.append(f"Battle begins: {char.name} vs {monster_state.name}!")
    battle.battle_log.append(
        f"Initiative: {char.name} ({player_init}) vs {monster_state.name} ({monster_init})")

    # If the monster won initiative it gets a free opening action
    if not battle.is_player_turn:
        execute_monster_turn(session)
        battle.is_player_turn = True
    return char.current_hit_points > 0


def begin_random_battle(session) -> bool:
    """Start a fight against a random monster from the current area."""
    area = session.current_area
    monster_race, level = get_monster_for_area(area, session.current_location)

    factory = MonsterFactory()
    if monster_race not in factory.races:
        monster_race = "Goblin"

    race_data = factory.races[monster_race]
    monster = factory.create_monster(
        name=random.choice(race_data.get("names", [monster_race])),
        race=monster_race,
        class_name=random.choice(race_data.get("class_options", ["Fighter"])),
        monster_level=level,
        weapon_name=random.choice(race_data.get("weapons", [race_data.get("weapon_name", "Club")])),
    )
    state = CombatantState.from_monster(monster)
    state.abilities = list(get_monster_abilities()["races"].get(monster_race, []))
    return begin_battle(session, state)


def begin_boss_battle(session, boss_id: str) -> bool:
    """Start a fight against a boss from bosses.json."""
    boss = get_bosses()[boss_id]
    state = CombatantState.from_boss(boss_id, boss)
    return begin_battle(session, state, intro_lines=[boss["intro"]] if boss.get("intro") else None)


def maybe_enrage(session):
    """Bosses enrage the first time they drop to half health."""
    monster = session.battle.monster
    if not monster.is_boss or monster.enraged or monster.hp <= 0:
        return
    if monster.hp * 2 > monster.max_hp:
        return
    monster.enraged = True
    monster.cooldowns = {}
    monster.effects.append({"stat": "damage_bonus", "value": 2 + monster.level // 5,
                            "duration": 0, "source": "Enraged"})
    boss = get_bosses().get(monster.boss_id, {})
    session.battle.battle_log.append(
        boss.get("enrage_text", f"{monster.name} flies into a rage!"))


def execute_monster_turn(session):
    """Execute the monster's turn: attack, defend or use a special ability."""
    battle = session.battle
    monster = battle.monster
    char = session.character
    catalog = get_monster_abilities()["abilities"]

    maybe_enrage(session)

    hp_fraction = char.current_hit_points / char.max_hit_points if char.max_hit_points else 1
    action, ability_id = choose_monster_action(monster, catalog, hp_fraction)

    if action == "ability":
        result = resolve_monster_ability(
            monster, ability_id, catalog[ability_id],
            player_ac=char.armor_class,
            player_effects=battle.player_effects,
            player_save_mods=get_save_modifiers(char),
        )
        battle.battle_log.extend(result["log"])
        if result["damage"]:
            char.current_hit_points = max(0, char.current_hit_points - result["damage"])

    elif action == "attack":
        ability_mod = get_weapon_attack_modifier(
            monster.str_mod, monster.dex_mod, monster.weapon.properties)

        result = resolve_weapon_attack(
            attacker_mod=ability_mod,
            attacker_prof=monster.proficiency,
            target_ac=char.armor_class,
            damage_dice_count=monster.weapon.damage_dice_count,
            damage_die=monster.weapon.damage_die,
            attacker_effects=monster.effects,
            target_effects=battle.player_effects,
        )

        battle.battle_log.append(f'{monster.name}: "{_taunt(battle, "attack")}"')
        if result["crit"]:
            battle.battle_log.append(
                f"{monster.name} attacks with {monster.weapon.name} — CRITICAL HIT! "
                f"{result['damage']} damage!")
        elif result["hit"]:
            battle.battle_log.append(
                f"{monster.name} attacks with {monster.weapon.name}! "
                f"(Roll: {result['attack_roll']} vs AC {result['target_ac']})")
            battle.battle_log.append(f"{monster.name} hits for {result['damage']} damage!")
        else:
            battle.battle_log.append(
                f"{monster.name} attacks with {monster.weapon.name}! "
                f"(Roll: {result['attack_roll']} vs AC {result['target_ac']})")
            battle.battle_log.append(f"{monster.name}'s attack misses!")
        if result["hit"]:
            char.current_hit_points = max(0, char.current_hit_points - result["damage"])

    else:
        monster.ac += 2
        battle.battle_log.append(f"{monster.name} takes a defensive stance (+2 AC).")


def _apply_round_conditions(session):
    """Apply end-of-round damage-over-time and regeneration to both sides."""
    battle = session.battle
    monster = battle.monster
    char = session.character

    for name, effects, is_monster in (
        (monster.name, monster.effects, True),
        (char.name, battle.player_effects, False),
    ):
        outcome = resolve_round_conditions(effects)
        for stat, value in outcome["sources"]:
            if stat in DOT_STATS:
                battle.battle_log.append(f"{name} takes {value} {stat} damage!")
            else:
                battle.battle_log.append(f"{name} regenerates {value} HP.")
        if is_monster:
            monster.hp = max(0, min(monster.max_hp, monster.hp - outcome["damage"] + outcome["heal"]))
        else:
            char.current_hit_points = max(0, min(
                char.max_hit_points, char.current_hit_points - outcome["damage"] + outcome["heal"]))


async def finish_player_turn(request: Request, session):
    """Resolve everything that follows the player's action.

    Monster turn → end-of-round conditions → effect/cooldown ticks → next round.
    If the player is stunned the loop repeats, costing them their turn.
    """
    battle = session.battle
    monster = battle.monster
    char = session.character

    if monster.hp <= 0:
        return await end_battle(request, session, player_won=True)

    while True:
        battle.is_player_turn = False
        if is_stunned(monster.effects):
            battle.battle_log.append(f"{monster.name} is stunned and loses its turn!")
        else:
            execute_monster_turn(session)

        if char.current_hit_points <= 0:
            return await end_battle(request, session, player_won=False)

        _apply_round_conditions(session)
        if monster.hp <= 0:
            return await end_battle(request, session, player_won=True)
        if char.current_hit_points <= 0:
            return await end_battle(request, session, player_won=False)
        maybe_enrage(session)

        # Round bookkeeping
        monster.reset_ac()
        battle.player_effects = tick_effects(battle.player_effects)
        monster.effects = tick_effects(monster.effects)
        tick_cooldowns(monster)
        battle.round_count += 1
        battle.is_player_turn = True

        if is_stunned(battle.player_effects):
            battle.battle_log.append(f"{char.name} is stunned and loses their turn!")
            continue
        break

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


# ---------------------------------------------------------------------------
# Starting battles
# ---------------------------------------------------------------------------

@router.get("/start")
async def start_battle(request: Request, session=Depends(require_character)):
    """Initialize a new random encounter in the current area."""
    if session.battle.is_active:
        return RedirectResponse("/battle", status_code=303)
    area = session.current_area
    if not area or not area.get("monster_types") or session.character.current_hit_points <= 0:
        return RedirectResponse("/game", status_code=303)

    if not begin_random_battle(session):
        return await end_battle(request, session, player_won=False)

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


@router.post("/boss")
async def start_boss_battle(request: Request, session=Depends(require_character)):
    """Challenge the boss guarding the current area."""
    if session.battle.is_active:
        return RedirectResponse("/battle", status_code=303)

    bosses = get_bosses()
    boss_id = campaign_rules.get_area_boss(session.current_area, bosses, session.defeated_bosses)
    if not boss_id or session.character.current_hit_points <= 0:
        return RedirectResponse("/game", status_code=303)
    if campaign_rules.missing_requirements(bosses[boss_id], session.defeated_bosses):
        return RedirectResponse("/game", status_code=303)

    if not begin_boss_battle(session, boss_id):
        return await end_battle(request, session, player_won=False)

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


# ---------------------------------------------------------------------------
# Battle view
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def battle_view(request: Request, session=Depends(require_battle)):
    """Battle view - show combat arena."""
    battle = session.battle
    monster = battle.monster
    char = session.character
    char_data = session.serialize_character()

    usable_items = [
        {"name": item.name, "description": item.description, "index": i}
        for i, item in enumerate(char.inventory)
        if hasattr(item, 'is_usable_in_battle') and item.is_usable_in_battle
    ]

    abilities = get_class_abilities(char.class_name, char.level)

    boss = get_bosses().get(monster.boss_id) if monster.is_boss else None
    portraits = get_monster_portraits()
    default_portrait = portraits.get("default", "/static/images/orc-creature-battle.jpg")
    monster_portrait = (boss or {}).get("portrait") or portraits.get(monster.race, default_portrait)
    monster_taunt = _taunt(battle, "start") if battle.round_count <= 1 else None

    log_entries = [{"text": entry, "cls": classify_log_entry(entry)}
                   for entry in battle.battle_log[-BATTLE_LOG_LIMIT:]]
    # A critical hit anywhere in the latest exchange shakes the screen
    had_crit = any(e["cls"] == "crit" for e in log_entries[-8:]) and battle.round_count > 1

    return templates.TemplateResponse(request, "battle/arena.html", {
        "request": request,
        "title": "Boss Battle!" if boss else "Battle!",
        "character": char_data,
        "monster": {
            "name": monster.name,
            "race": monster.race,
            "level": monster.level,
            "hp": monster.hp,
            "max_hp": monster.max_hp,
            "ac": monster.ac + get_effect_bonus(monster.effects, "ac"),
            "portrait": monster_portrait,
            "taunt": monster_taunt,
            "is_boss": monster.is_boss,
            "title": boss.get("title") if boss else None,
            "enraged": monster.enraged,
        },
        "player_ac": char.armor_class + get_effect_bonus(battle.player_effects, "ac"),
        "round": battle.round_count,
        "battle_log": log_entries,
        "had_crit": had_crit,
        "is_player_turn": battle.is_player_turn,
        "usable_items": usable_items,
        "abilities": abilities,
        "player_effects": effect_badges(battle.player_effects),
        "monster_effects": effect_badges(monster.effects),
        "flee_dc": 10 + monster.level // 2,
        "flee_mod": char.dexterity_modifier,
    })


# ---------------------------------------------------------------------------
# Player actions
# ---------------------------------------------------------------------------

@router.post("/attack")
async def player_attack(request: Request, session=Depends(require_battle)):
    """Player attacks the monster."""
    if not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character
    battle = session.battle
    monster = battle.monster

    weapon = char.weapon_slots.get(WeaponSlot.MAIN_HAND)
    if weapon:
        ability_mod = char.get_attack_modifier(weapon)
        damage_die = weapon.damage_die
        damage_dice_count = weapon.damage_dice_count
    else:
        ability_mod = char.strength_modifier
        damage_die = 4
        damage_dice_count = 1

    result = resolve_weapon_attack(
        attacker_mod=ability_mod,
        attacker_prof=char.proficiency_bonus,
        target_ac=monster.ac,
        damage_dice_count=damage_dice_count,
        damage_die=damage_die,
        attacker_effects=battle.player_effects,
        target_effects=monster.effects,
    )

    if result["crit"]:
        battle.battle_log.append(
            f"{char.name} attacks — CRITICAL HIT! {result['damage']} damage!")
    else:
        battle.battle_log.append(
            f"{char.name} attacks! (Roll: {result['attack_roll']} vs AC {result['target_ac']})")
        if result["hit"]:
            battle.battle_log.append(f"{char.name} hits for {result['damage']} damage!")
        elif result["fumble"]:
            battle.battle_log.append(f"{char.name} fumbles — the attack misses badly!")
        else:
            battle.battle_log.append(f"{char.name}'s attack misses!")

    if result["hit"]:
        monster.hp = max(0, monster.hp - result["damage"])
        if monster.hp > 0:
            battle.battle_log.append(f'{monster.name}: "{_taunt(battle, "hurt")}"')

    return await finish_player_turn(request, session)


@router.post("/defend")
async def player_defend(request: Request, session=Depends(require_battle)):
    """Player takes a defensive stance: +1d4 AC until the end of the round."""
    if not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character
    ac_bonus = Dice.roll_d4()
    session.battle.player_effects.append(
        {"stat": "ac", "value": ac_bonus, "duration": 1, "source": "Defend"})
    session.battle.battle_log.append(f"{char.name} takes a defensive stance (+{ac_bonus} AC)!")

    return await finish_player_turn(request, session)


@router.post("/item")
async def use_item(request: Request, item_index: int = Form(...), session=Depends(require_battle)):
    """Use an item during battle."""
    if not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character
    item = char.inventory[item_index] if 0 <= item_index < len(char.inventory) else None
    if not isinstance(item, HealingPotion):
        # Nothing usable at that slot — don't waste the player's turn
        return RedirectResponse("/battle", status_code=303)

    old_hp = char.current_hit_points
    char.current_hit_points = min(char.max_hit_points, old_hp + item.healing_amount)
    char.inventory.pop(item_index)
    session.battle.battle_log.append(
        f"{char.name} uses {item.name} and heals for {char.current_hit_points - old_hp} HP!")

    return await finish_player_turn(request, session)


def resolve_ability(session, ability) -> bool:
    """Resolve a class ability. Returns True if the ability was successfully used."""
    log = resolve_player_ability(
        session.character, ability, session.battle.monster,
        session.battle.player_effects, get_primary_modifier(session.character))
    if log is None:
        return False
    session.battle.battle_log.extend(log)
    return True


@router.post("/ability")
async def use_ability(request: Request, ability_id: str = Form(...), session=Depends(require_battle)):
    """Use a class ability in battle."""
    if not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    ability = get_abilities().get(ability_id)
    if not ability:
        return RedirectResponse("/battle", status_code=303)

    # Verify class can use this ability and level is sufficient
    char = session.character
    if char.class_name not in ability.get("classes", []):
        return RedirectResponse("/battle", status_code=303)
    if char.level < ability.get("unlock_level", 1):
        return RedirectResponse("/battle", status_code=303)

    if not resolve_ability(session, ability):
        return RedirectResponse("/battle", status_code=303)

    return await finish_player_turn(request, session)


@router.post("/flee")
async def flee(request: Request, session=Depends(require_battle)):
    """Try to escape: d20 + DEX vs DC 10 + half the monster's level. Bosses can't be fled."""
    battle = session.battle
    if not battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character
    if battle.monster.is_boss:
        battle.battle_log.append("There is no escape from this fight!")
        save_session(request, session)
        return RedirectResponse("/battle", status_code=303)

    result = resolve_flee(char.dexterity_modifier, battle.monster.level)
    if result["success"]:
        battle.is_active = False
        battle.player_effects = []
        battle.monster.effects = []
        char.active_effects = []
        session.set_flash("game_message", {
            "text": f"You slip away from {battle.monster.name}! "
                    f"(Rolled {result['total']} vs DC {result['dc']})",
            "type": "info"})
        save_session(request, session)
        return RedirectResponse("/game", status_code=303)

    battle.battle_log.append(
        f"{char.name} tries to flee but {battle.monster.name} cuts off the escape! "
        f"(Rolled {result['total']} vs DC {result['dc']})")
    return await finish_player_turn(request, session)


# ---------------------------------------------------------------------------
# Battle resolution
# ---------------------------------------------------------------------------

def _boss_victory(session, boss_id: str) -> dict:
    """Record a boss kill and work out what it unlocked. Returns display data."""
    bosses = get_bosses()
    boss = bosses[boss_id]
    campaign = get_campaign()

    act_before = campaign_rules.highest_unlocked_act(campaign, session.defeated_bosses)
    complete_before = campaign_rules.is_campaign_complete(campaign, session.defeated_bosses)
    if boss_id not in session.defeated_bosses:
        session.defeated_bosses.append(boss_id)
    act_after = campaign_rules.highest_unlocked_act(campaign, session.defeated_bosses)

    act_unlocked = None
    if act_after > act_before:
        act = next(a for a in campaign["acts"] if a["number"] == act_after)
        act_unlocked = {"number": act["number"], "title": act["title"],
                        "description": act["description"]}

    return {
        "name": boss["name"],
        "defeat_text": boss.get("defeat_text"),
        "shard": boss.get("shard"),
        "shards_collected": len(campaign_rules.collected_shards(bosses, session.defeated_bosses)),
        "shards_total": len(campaign_rules.all_shards(bosses)),
        "act_unlocked": act_unlocked,
        "campaign_complete": (not complete_before
                              and campaign_rules.is_campaign_complete(campaign, session.defeated_bosses)),
    }


async def end_battle(request: Request, session, player_won: bool):
    """End the battle and show results."""
    battle = session.battle
    monster = battle.monster
    char = session.character

    battle.is_active = False
    battle.player_effects = []
    monster.effects = []
    char.active_effects = []

    if player_won:
        boss = get_bosses().get(monster.boss_id) if monster.is_boss else None
        if boss:
            xp_reward = boss.get("rewards", {}).get("xp", 300 * monster.level)
            gold_reward = boss.get("rewards", {}).get("gold", 30 * monster.level)
        else:
            xp_reward = calculate_xp_reward(monster.level, battle.round_count)
            gold_reward = calculate_gold_reward(monster.level)

        abilities_before = {a["id"] for a in get_class_abilities(char.class_name, char.level)}
        xp_result = grant_xp(char, xp_reward, get_primary_modifier(char))
        new_abilities = [a["name"] for a in get_class_abilities(char.class_name, char.level)
                         if a["id"] not in abilities_before]

        char.gold += gold_reward
        session.monster_kills += 1

        # Restock shop every 10 kills
        if session.monster_kills - session.kills_at_last_restock >= 10:
            restock_shop(session)
            session.kills_at_last_restock = session.monster_kills

        # Loot — bosses always drop something, from a better table
        loot_level = monster.level + 6 if boss else monster.level
        loot = LootGenerator().generate_loot(loot_level, char.level)
        if loot:
            if loot["type"] == "gold":
                char.gold += loot["amount"]
            else:
                char.add_item(loot["item"])

        quest_updates = check_quest_progress(
            session.active_quests, get_quests(), monster.race, char.inventory)

        session.battle_rewards = {
            "xp": xp_reward,
            "gold": gold_reward,
            "loot": loot["message"] if loot else None,
            "loot_type": loot["type"] if loot else None,
            "leveled_up": xp_result["leveled_up"],
            "new_level": char.level,
            "hp_increase": xp_result["hp_increase"],
            "new_abilities": new_abilities,
            "new_max_pp": char.max_power_points if xp_result["leveled_up"] else None,
            "quest_updates": quest_updates,
            "boss": _boss_victory(session, monster.boss_id) if boss else None,
        }
    else:
        session.battle_rewards = None
        restock_shop(session)
        session.kills_at_last_restock = session.monster_kills

    save_session(request, session)

    if player_won:
        return RedirectResponse("/battle/victory", status_code=303)
    else:
        return RedirectResponse("/battle/defeat", status_code=303)


@router.get("/victory", response_class=HTMLResponse)
async def victory_screen(request: Request, session=Depends(require_character)):
    """Display victory screen with rewards."""
    rewards = session.battle_rewards or {}
    session.battle_rewards = None
    save_session(request, session)
    char_data = session.serialize_character() if session.character else None

    return templates.TemplateResponse(request, "battle/victory.html", {
        "request": request,
        "title": "Victory!",
        "character": char_data,
        "rewards": rewards,
        "monster_name": session.battle.monster_name
    })


@router.get("/defeat", response_class=HTMLResponse)
async def defeat_screen(request: Request, session=Depends(require_character)):
    """Display defeat screen."""
    session.battle_rewards = None
    save_session(request, session)
    char_data = session.serialize_character() if session.character else None

    gold = session.character.gold if session.character else 0
    gold_cost = gold // 2

    return templates.TemplateResponse(request, "battle/defeat.html", {
        "request": request,
        "title": "Defeat",
        "character": char_data,
        "monster_name": session.battle.monster_name,
        "gold_cost": gold_cost,
        "current_gold": gold,
    })


@router.post("/revive")
async def revive(request: Request, session=Depends(require_character)):
    """Revive the character at the current location's starting area."""
    char = session.character
    if not char or char.current_hit_points > 0:
        return RedirectResponse("/game", status_code=303)

    # Gold penalty: lose 50%
    char.gold = char.gold - (char.gold // 2)

    # Heal to full
    char.current_hit_points = char.max_hit_points
    char.power_points = char.max_power_points
    char.active_effects = []

    # Move to starting area of current location
    location = session.current_location
    if location:
        starting_id = location.get("starting_area")
        if starting_id:
            for area in location.get("areas", []):
                if area["id"] == starting_id:
                    session.current_area = area
                    break

    save_session(request, session)
    return RedirectResponse("/game?revived=true", status_code=303)


@router.get("/status")
async def battle_status(request: Request):
    """Get current battle status as JSON."""
    session = get_session(request)

    if not session.battle.is_active:
        return {"active": False}

    return {
        "active": True,
        "player": {
            "current_hp": session.character.current_hit_points,
            "max_hp": session.character.max_hit_points
        },
        "monster": {
            "current_hp": session.battle.monster_hp,
            "max_hp": session.battle.monster_max_hp
        },
        "round": session.battle.round_count,
        "is_player_turn": session.battle.is_player_turn
    }
