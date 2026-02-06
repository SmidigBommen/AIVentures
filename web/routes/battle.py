import sys
import random
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session
from monsterFactory import MonsterFactory
from dice import Dice
from items import HealingPotion
from character import WeaponSlot

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


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


@router.get("/start")
async def start_battle(request: Request):
    """Initialize a new battle encounter."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    area = session.current_area
    if not area:
        return RedirectResponse("/game", status_code=303)

    # Generate monster
    location = session.current_location
    monster_race, level = get_monster_for_area(area, location)

    # Create monster using factory
    factory = MonsterFactory()

    # Make sure monster_race exists in defaults, fallback to Goblin
    if monster_race not in factory.races:
        monster_race = "Goblin"

    race_data = factory.races[monster_race]
    monster_name = random.choice(race_data.get("names", [monster_race]))
    monster_class = random.choice(race_data.get("class_options", ["Fighter"]))
    weapon_name = random.choice(race_data.get("weapons", [race_data.get("weapon_name", "Club")]))

    monster = factory.create_monster(
        name=monster_name,
        race=monster_race,
        class_name=monster_class,
        monster_level=level,
        weapon_name=weapon_name
    )

    # Initialize battle state
    session.battle.is_active = True
    session.battle.monster_name = monster.name
    session.battle.monster_race = monster.race
    session.battle.monster_level = monster.level
    session.battle.monster_hp = monster.current_hit_points
    session.battle.monster_max_hp = monster.max_hit_points
    session.battle.monster_ac = monster.armor_class
    session.battle.monster_base_ac = monster.base_ac
    session.battle.monster_dex_modifier = monster.dexterity_modifier
    session.battle.monster_str_modifier = monster.strength_modifier
    session.battle.monster_proficiency_bonus = monster.proficiency_bonus
    session.battle.monster_weapon_name = monster.weapon.name
    session.battle.monster_weapon_damage_die = monster.weapon.damage_die
    session.battle.monster_weapon_damage_dice_count = monster.weapon.damage_dice_count
    session.battle.monster_weapon_properties = monster.weapon.properties
    session.battle.round_count = 1
    session.battle.battle_log = []

    # Calculate initiative
    player_init = session.character.dexterity_modifier + Dice.roll_d20()
    monster_init = monster.dexterity_modifier + Dice.roll_d20()

    session.battle.initiative_order = [
        ("player", player_init),
        ("monster", monster_init)
    ]
    session.battle.initiative_order.sort(key=lambda x: x[1], reverse=True)
    session.battle.is_player_turn = session.battle.initiative_order[0][0] == "player"

    session.battle.battle_log.append(f"Battle begins: {session.character.name} vs {monster.name}!")
    session.battle.battle_log.append(f"Initiative: {session.character.name} ({player_init}) vs {monster.name} ({monster_init})")

    # If monster goes first, execute monster turn
    if not session.battle.is_player_turn:
        execute_monster_turn(session)
        session.battle.is_player_turn = True

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


def get_monster_attack_modifier(battle):
    """Return the correct ability modifier for the monster's weapon."""
    props = battle.monster_weapon_properties
    if "ammunition" in props:
        return battle.monster_dex_modifier
    if "finesse" in props:
        return max(battle.monster_str_modifier, battle.monster_dex_modifier)
    return battle.monster_str_modifier


def execute_monster_turn(session):
    """Execute the monster's turn."""
    # Simple AI: 70% attack, 30% defend
    action = random.random()

    if action < 0.7:
        # Attack
        battle = session.battle
        ability_mod = get_monster_attack_modifier(battle)
        attack_roll = Dice.roll_d20() + ability_mod + battle.monster_proficiency_bonus
        session.battle.battle_log.append(f"{battle.monster_name} attacks with {battle.monster_weapon_name}! (Roll: {attack_roll} vs AC {session.character.armor_class})")

        if attack_roll >= session.character.armor_class:
            # Hit - calculate damage using actual weapon dice
            damage = 0
            for _ in range(battle.monster_weapon_damage_dice_count):
                damage += Dice.roll(battle.monster_weapon_damage_die)
            damage = max(1, damage + ability_mod)
            session.character.current_hit_points = max(0, session.character.current_hit_points - damage)
            session.battle.battle_log.append(f"{battle.monster_name} hits for {damage} damage!")
        else:
            session.battle.battle_log.append(f"{battle.monster_name}'s attack misses!")
    else:
        # Defend
        session.battle.monster_ac += 2
        session.battle.battle_log.append(f"{session.battle.monster_name} takes a defensive stance (+2 AC).")


@router.get("/", response_class=HTMLResponse)
async def battle_view(request: Request):
    """Battle view - show combat arena."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    if not session.battle.is_active:
        return RedirectResponse("/game", status_code=303)

    char_data = session._serialize_character()

    # Get usable items
    usable_items = [
        {"name": item.name, "description": item.description, "index": i}
        for i, item in enumerate(session.character.inventory)
        if hasattr(item, 'is_usable_in_battle') and item.is_usable_in_battle
    ]

    return templates.TemplateResponse("battle/arena.html", {
        "request": request,
        "title": "Battle!",
        "character": char_data,
        "monster": {
            "name": session.battle.monster_name,
            "race": session.battle.monster_race,
            "level": session.battle.monster_level,
            "hp": session.battle.monster_hp,
            "max_hp": session.battle.monster_max_hp,
            "ac": session.battle.monster_ac
        },
        "round": session.battle.round_count,
        "battle_log": session.battle.battle_log[-10:],  # Last 10 entries
        "is_player_turn": session.battle.is_player_turn,
        "usable_items": usable_items
    })


@router.post("/attack")
async def player_attack(request: Request):
    """Player attacks the monster."""
    session = get_session(request)

    if not session.battle.is_active or not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character

    # Get weapon damage
    weapon = char.weapon_slots.get(WeaponSlot.MAIN_HAND)
    if weapon:
        damage_die = weapon.damage_die
        damage_dice_count = weapon.damage_dice_count
    else:
        damage_die = 4
        damage_dice_count = 1

    # Attack roll
    if weapon:
        ability_mod = char.get_attack_modifier(weapon)
    else:
        ability_mod = char.strength_modifier
    attack_roll = Dice.roll_d20() + ability_mod + char.proficiency_bonus
    session.battle.battle_log.append(f"{char.name} attacks! (Roll: {attack_roll} vs AC {session.battle.monster_ac})")

    if attack_roll >= session.battle.monster_ac:
        # Calculate damage
        damage = 0
        for _ in range(damage_dice_count):
            damage += Dice.roll(damage_die)
        damage = max(1, damage + ability_mod)

        session.battle.monster_hp = max(0, session.battle.monster_hp - damage)
        session.battle.battle_log.append(f"{char.name} hits for {damage} damage!")
    else:
        session.battle.battle_log.append(f"{char.name}'s attack misses!")

    # Check for victory
    if session.battle.monster_hp <= 0:
        return await end_battle(request, session, player_won=True)

    # Monster's turn
    session.battle.is_player_turn = False
    execute_monster_turn(session)

    # Check for defeat
    if char.current_hit_points <= 0:
        return await end_battle(request, session, player_won=False)

    # Reset monster AC and advance round
    session.battle.monster_ac = session.battle.monster_base_ac + session.battle.monster_dex_modifier
    session.battle.round_count += 1
    session.battle.is_player_turn = True

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


@router.post("/defend")
async def player_defend(request: Request):
    """Player takes a defensive stance."""
    session = get_session(request)

    if not session.battle.is_active or not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character

    # Gain AC bonus
    ac_bonus = Dice.roll_d4()
    char.armor_class += ac_bonus
    session.battle.battle_log.append(f"{char.name} takes a defensive stance (+{ac_bonus} AC)!")

    # Monster's turn
    session.battle.is_player_turn = False
    execute_monster_turn(session)

    # Check for defeat
    if char.current_hit_points <= 0:
        return await end_battle(request, session, player_won=False)

    # Reset AC bonus and advance round
    char.armor_class -= ac_bonus
    session.battle.monster_ac = session.battle.monster_base_ac + session.battle.monster_dex_modifier
    session.battle.round_count += 1
    session.battle.is_player_turn = True

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


@router.post("/item")
async def use_item(request: Request, item_index: int = Form(...)):
    """Use an item during battle."""
    session = get_session(request)

    if not session.battle.is_active or not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    char = session.character

    if 0 <= item_index < len(char.inventory):
        item = char.inventory[item_index]
        if hasattr(item, 'is_usable_in_battle') and item.is_usable_in_battle:
            if isinstance(item, HealingPotion):
                heal_amount = item.healing_amount
                old_hp = char.current_hit_points
                char.current_hit_points = min(char.max_hit_points, char.current_hit_points + heal_amount)
                actual_heal = char.current_hit_points - old_hp
                char.inventory.pop(item_index)
                session.battle.battle_log.append(f"{char.name} uses {item.name} and heals for {actual_heal} HP!")

    # Monster's turn
    session.battle.is_player_turn = False
    execute_monster_turn(session)

    # Check for defeat
    if char.current_hit_points <= 0:
        return await end_battle(request, session, player_won=False)

    # Advance round
    session.battle.monster_ac = session.battle.monster_base_ac + session.battle.monster_dex_modifier
    session.battle.round_count += 1
    session.battle.is_player_turn = True

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


async def end_battle(request: Request, session, player_won: bool):
    """End the battle and show results."""
    session.battle.is_active = False

    if player_won:
        # Calculate rewards
        base_xp = 100 * session.battle.monster_level
        round_bonus = max(0, 10 * (10 - session.battle.round_count))
        xp_reward = base_xp + round_bonus

        base_gold = session.battle.monster_level * 5
        gold_reward = base_gold + Dice.roll_d8()

        # Apply rewards
        old_level = session.character.level
        session.character.xp += xp_reward
        # Check for level up
        while session.character.xp >= session.character.xp_to_next_level:
            session.character.level += 1
            session.character.xp -= session.character.xp_to_next_level
            session.character.xp_to_next_level = session.character.level * 150
            # Auto increase HP on level up
            hp_increase = max(1, (session.character.hit_die // 2) + 1 + session.character.constitution_modifier)
            session.character.max_hit_points += hp_increase
            session.character.current_hit_points += hp_increase

        session.character.gold += gold_reward
        session.monster_kills += 1

        # Chance for loot
        loot = None
        if random.random() < 0.2:
            loot = "Healing Potion"
            session.character.add_item(HealingPotion("Healing Potion", 10))

        # Store rewards in session for display
        request.session["battle_rewards"] = {
            "xp": xp_reward,
            "gold": gold_reward,
            "loot": loot,
            "leveled_up": session.character.level > old_level,
            "new_level": session.character.level
        }
    else:
        request.session["battle_rewards"] = None

    save_session(request, session)

    if player_won:
        return RedirectResponse("/battle/victory", status_code=303)
    else:
        return RedirectResponse("/battle/defeat", status_code=303)


@router.get("/victory", response_class=HTMLResponse)
async def victory_screen(request: Request):
    """Display victory screen with rewards."""
    session = get_session(request)
    rewards = request.session.get("battle_rewards", {})
    char_data = session._serialize_character() if session.character else None

    return templates.TemplateResponse("battle/victory.html", {
        "request": request,
        "title": "Victory!",
        "character": char_data,
        "rewards": rewards,
        "monster_name": session.battle.monster_name
    })


@router.get("/defeat", response_class=HTMLResponse)
async def defeat_screen(request: Request):
    """Display defeat screen."""
    session = get_session(request)
    char_data = session._serialize_character() if session.character else None

    return templates.TemplateResponse("battle/defeat.html", {
        "request": request,
        "title": "Defeat",
        "character": char_data,
        "monster_name": session.battle.monster_name
    })


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
