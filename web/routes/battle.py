import sys
import random
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session, get_abilities, get_class_abilities, get_primary_modifier, calculate_max_pp
from monsterFactory import MonsterFactory
from dice import Dice
from items import HealingPotion
from character import WeaponSlot
from lootGenerator import LootGenerator
from web.routes.shop import restock_shop

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
        # Attack (apply monster's active effect bonuses)
        battle = session.battle
        ability_mod = get_monster_attack_modifier(battle)
        monster_atk_bonus = get_effect_bonus(battle.monster_effects, "attack_bonus")
        player_ac = session.character.armor_class + get_effect_bonus(battle.player_effects, "ac")
        attack_roll = Dice.roll_d20() + ability_mod + battle.monster_proficiency_bonus + monster_atk_bonus
        session.battle.battle_log.append(f"{battle.monster_name} attacks with {battle.monster_weapon_name}! (Roll: {attack_roll} vs AC {player_ac})")

        if attack_roll >= player_ac:
            # Hit - calculate damage using actual weapon dice
            damage = 0
            for _ in range(battle.monster_weapon_damage_dice_count):
                damage += Dice.roll(battle.monster_weapon_damage_die)
            monster_dmg_bonus = get_effect_bonus(battle.monster_effects, "damage_bonus")
            damage = max(1, damage + ability_mod + monster_dmg_bonus)
            player_dr = get_effect_bonus(battle.player_effects, "damage_reduction")
            damage = max(1, damage - player_dr)
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

    # Get class abilities
    char = session.character
    abilities = get_class_abilities(char.class_name, char.level)

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
        "battle_log": session.battle.battle_log[-10:],
        "is_player_turn": session.battle.is_player_turn,
        "usable_items": usable_items,
        "abilities": abilities,
        "player_effects": session.battle.player_effects,
        "monster_effects": session.battle.monster_effects,
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

    # Attack roll (apply active effect bonuses)
    if weapon:
        ability_mod = char.get_attack_modifier(weapon)
    else:
        ability_mod = char.strength_modifier
    atk_bonus = get_effect_bonus(session.battle.player_effects, "attack_bonus")
    effective_monster_ac = session.battle.monster_ac + get_effect_bonus(session.battle.monster_effects, "ac")
    attack_roll = Dice.roll_d20() + ability_mod + char.proficiency_bonus + atk_bonus
    session.battle.battle_log.append(f"{char.name} attacks! (Roll: {attack_roll} vs AC {effective_monster_ac})")

    if attack_roll >= effective_monster_ac:
        # Calculate damage (apply damage bonus effects)
        damage = 0
        for _ in range(damage_dice_count):
            damage += Dice.roll(damage_die)
        dmg_bonus = get_effect_bonus(session.battle.player_effects, "damage_bonus")
        damage = max(1, damage + ability_mod + dmg_bonus)

        dr = get_effect_bonus(session.battle.monster_effects, "damage_reduction")
        damage = max(1, damage - dr)
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

    # Reset monster AC, tick effects, advance round
    session.battle.monster_ac = session.battle.monster_base_ac + session.battle.monster_dex_modifier
    session.battle.player_effects = tick_effects(session.battle.player_effects)
    session.battle.monster_effects = tick_effects(session.battle.monster_effects)
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

    # Reset AC bonus, tick effects, advance round
    char.armor_class -= ac_bonus
    session.battle.monster_ac = session.battle.monster_base_ac + session.battle.monster_dex_modifier
    session.battle.player_effects = tick_effects(session.battle.player_effects)
    session.battle.monster_effects = tick_effects(session.battle.monster_effects)
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

    # Advance round, tick effects
    session.battle.monster_ac = session.battle.monster_base_ac + session.battle.monster_dex_modifier
    session.battle.player_effects = tick_effects(session.battle.player_effects)
    session.battle.monster_effects = tick_effects(session.battle.monster_effects)
    session.battle.round_count += 1
    session.battle.is_player_turn = True

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


def get_effect_bonus(effects, stat):
    """Sum all active effect bonuses for a stat."""
    return sum(e["value"] for e in effects if e["stat"] == stat)


def tick_effects(effects):
    """Decrement durations and remove expired effects. Duration 0 = lasts entire combat."""
    remaining = []
    for e in effects:
        if e["duration"] == 0:
            remaining.append(e)
        elif e["duration"] > 1:
            remaining.append({**e, "duration": e["duration"] - 1})
        # duration == 1 means it expires this round, so we drop it
    return remaining


def resolve_ability(session, ability, ability_id):
    """Resolve an ability use. Returns True if the ability was successfully used."""
    char = session.character
    battle = session.battle
    primary_mod = get_primary_modifier(char)

    # Check PP
    if char.power_points < ability["cost"]:
        return False

    # Spend PP
    char.power_points -= ability["cost"]

    attack_method = ability["attack_method"]
    target = ability["target"]

    # Determine if attack hits (for damage abilities targeting enemies)
    hit = True
    if target == "enemy" and attack_method in ("melee_attack", "spell_attack"):
        attack_bonus = get_effect_bonus(battle.player_effects, "attack_bonus")
        attack_roll = Dice.roll_d20() + primary_mod + char.proficiency_bonus + attack_bonus
        effective_ac = battle.monster_ac + get_effect_bonus(battle.monster_effects, "ac")
        if attack_roll >= effective_ac:
            battle.battle_log.append(f"{char.name} uses {ability['name']}! (Roll: {attack_roll} vs AC {effective_ac}) Hit!")
        else:
            battle.battle_log.append(f"{char.name} uses {ability['name']}! (Roll: {attack_roll} vs AC {effective_ac}) Miss!")
            hit = False

    elif target == "enemy" and attack_method == "spell_save":
        spell_dc = 8 + primary_mod + char.proficiency_bonus
        save_ability = ability.get("save_ability", "Dexterity").lower()
        save_mod = getattr(battle, f"monster_{save_ability[:3]}_modifier", 0)
        save_roll = Dice.roll_d20() + save_mod
        if save_roll >= spell_dc:
            battle.battle_log.append(f"{char.name} casts {ability['name']}! ({battle.monster_name} saves: {save_roll} vs DC {spell_dc}) Half damage!")
            hit = False  # save = half damage, we handle below
        else:
            battle.battle_log.append(f"{char.name} casts {ability['name']}! ({battle.monster_name} fails save: {save_roll} vs DC {spell_dc})")

    elif target == "self":
        battle.battle_log.append(f"{char.name} uses {ability['name']}!")

    elif attack_method == "auto_hit":
        battle.battle_log.append(f"{char.name} uses {ability['name']}!")

    # Apply damage
    if ability.get("damage") and target == "enemy":
        dmg_data = ability["damage"]
        dice_count = dmg_data["dice_count"]

        # Apply scaling for cantrips
        if ability.get("scaling"):
            for level_str in sorted(ability["scaling"].keys(), key=int, reverse=True):
                if char.level >= int(level_str):
                    dice_count = ability["scaling"][level_str].get("dice_count", dice_count)
                    break

        damage = 0
        for _ in range(dice_count):
            damage += Dice.roll(dmg_data["dice_size"])

        # Add bonus
        bonus = dmg_data.get("bonus", 0)
        if bonus == "ability_modifier":
            damage += primary_mod
        elif bonus == "level":
            damage += char.level
        elif isinstance(bonus, int):
            damage += bonus

        damage = max(1, damage)
        damage_bonus = get_effect_bonus(battle.player_effects, "damage_bonus")
        damage += damage_bonus

        # Spell save = half damage on successful save
        if attack_method == "spell_save" and not hit:
            damage = max(1, damage // 2)
            hit = True  # still apply the (halved) damage

        # Melee/spell attack miss = no damage
        if hit:
            dr = get_effect_bonus(battle.monster_effects, "damage_reduction")
            damage = max(1, damage - dr)
            battle.monster_hp = max(0, battle.monster_hp - damage)
            battle.battle_log.append(f"  {ability['name']} deals {damage} {dmg_data.get('type', '')} damage!")

    # Apply heal
    if ability.get("heal"):
        heal_data = ability["heal"]
        heal = 0
        for _ in range(heal_data["dice_count"]):
            heal += Dice.roll(heal_data["dice_size"])
        bonus = heal_data.get("bonus", 0)
        if bonus == "ability_modifier":
            heal += primary_mod
        elif bonus == "level":
            heal += char.level
        elif isinstance(bonus, int):
            heal += bonus
        heal = max(1, heal)
        old_hp = char.current_hit_points
        char.current_hit_points = min(char.max_hit_points, char.current_hit_points + heal)
        actual_heal = char.current_hit_points - old_hp
        if actual_heal > 0:
            battle.battle_log.append(f"  {char.name} heals for {actual_heal} HP!")

    # Apply effects
    for effect in ability.get("effects", []):
        eff = {"stat": effect["stat"], "value": effect["value"],
               "duration": effect["duration"], "source": ability["name"]}
        if target == "enemy":
            battle.monster_effects.append(eff)
            battle.battle_log.append(f"  {battle.monster_name}: {effect['stat'].replace('_', ' ')} {effect['value']:+d}")
        else:
            battle.player_effects.append(eff)
            if effect["value"] > 0:
                battle.battle_log.append(f"  {char.name}: {effect['stat'].replace('_', ' ')} {effect['value']:+d}")

    return True


@router.post("/ability")
async def use_ability(request: Request, ability_id: str = Form(...)):
    """Use a class ability in battle."""
    session = get_session(request)

    if not session.battle.is_active or not session.battle.is_player_turn:
        return RedirectResponse("/battle", status_code=303)

    abilities = get_abilities()
    ability = abilities.get(ability_id)

    if not ability:
        return RedirectResponse("/battle", status_code=303)

    # Verify class can use this ability and level is sufficient
    char = session.character
    if char.class_name not in ability.get("classes", []):
        return RedirectResponse("/battle", status_code=303)
    if char.level < ability.get("unlock_level", 1):
        return RedirectResponse("/battle", status_code=303)

    if not resolve_ability(session, ability, ability_id):
        return RedirectResponse("/battle", status_code=303)

    # Check for victory
    if session.battle.monster_hp <= 0:
        return await end_battle(request, session, player_won=True)

    # Monster's turn
    session.battle.is_player_turn = False
    execute_monster_turn(session)

    # Check for defeat
    if char.current_hit_points <= 0:
        return await end_battle(request, session, player_won=False)

    # Tick effect durations and advance round
    session.battle.player_effects = tick_effects(session.battle.player_effects)
    session.battle.monster_effects = tick_effects(session.battle.monster_effects)
    session.battle.round_count += 1
    session.battle.is_player_turn = True

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)


async def end_battle(request: Request, session, player_won: bool):
    """End the battle and show results."""
    session.battle.is_active = False
    session.battle.player_effects = []
    session.battle.monster_effects = []
    if session.character:
        session.character.active_effects = []

    if player_won:
        # Calculate rewards
        base_xp = 100 * session.battle.monster_level
        round_bonus = max(0, 10 * (10 - session.battle.round_count))
        xp_reward = base_xp + round_bonus

        base_gold = session.battle.monster_level * 5
        gold_reward = base_gold + Dice.roll_d8()

        # Apply rewards
        old_level = session.character.level
        total_hp_increase = 0
        abilities_before = get_class_abilities(session.character.class_name, old_level)
        abilities_before_ids = {a["id"] for a in abilities_before}

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
            total_hp_increase += hp_increase

        # Recalculate PP on level up
        if session.character.level > old_level:
            primary_mod = get_primary_modifier(session.character)
            session.character.max_power_points = calculate_max_pp(session.character.class_name, session.character.level, primary_mod)
            session.character.power_points = session.character.max_power_points

        # Find newly unlocked abilities
        abilities_after = get_class_abilities(session.character.class_name, session.character.level)
        new_abilities = [a["name"] for a in abilities_after if a["id"] not in abilities_before_ids]

        session.character.gold += gold_reward
        session.monster_kills += 1

        # Restock shop every 10 kills
        if session.monster_kills - session.kills_at_last_restock >= 10:
            restock_shop(request)
            session.kills_at_last_restock = session.monster_kills

        # Chance for loot
        loot = LootGenerator().generate_loot(session.battle.monster_level, session.character.level)
        if loot:
            if loot["type"] == "gold":
                session.character.gold += loot["amount"]
            else:
                session.character.add_item(loot["item"])

        # Store rewards in session for display
        request.session["battle_rewards"] = {
            "xp": xp_reward,
            "gold": gold_reward,
            "loot": loot["message"] if loot else None,
            "loot_type": loot["type"] if loot else None,
            "leveled_up": session.character.level > old_level,
            "new_level": session.character.level,
            "hp_increase": total_hp_increase,
            "new_abilities": new_abilities,
            "new_max_pp": session.character.max_power_points if session.character.level > old_level else None
        }
    else:
        request.session["battle_rewards"] = None
        restock_shop(request)
        session.kills_at_last_restock = session.monster_kills

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
