import sys
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import (
    get_session, save_session, get_races, get_classes,
    get_all_weapons_flat, get_all_armors_flat, get_campaign
)
from characterFactory import CharacterFactory
from weaponFactory import WeaponFactory
from armorFactory import ArmorFactory
from items import HealingPotion
from character import WeaponSlot

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/new", response_class=HTMLResponse)
async def new_character(request: Request):
    """Start character creation - show race selection."""
    # Reset character creation state
    session = get_session(request)
    session.character_creation.race = None
    session.character_creation.class_name = None
    session.character_creation.name = None
    session.character_creation.weapon = None
    session.character_creation.armor = None
    session.character_creation.skills = []
    session.character = None
    save_session(request, session)

    races = get_races()

    # Format race data for display
    race_list = []
    for race_name, bonuses in races.items():
        bonus_str = []
        for stat, value in bonuses.items():
            if value > 0:
                stat_name = stat.replace("_bonus", "").upper()[:3]
                bonus_str.append(f"+{value} {stat_name}")
        race_list.append({
            "name": race_name,
            "bonuses": bonuses,
            "bonus_display": ", ".join(bonus_str) if bonus_str else "No bonuses"
        })

    return templates.TemplateResponse("character/select_race.html", {
        "request": request,
        "title": "Choose Your Race",
        "races": race_list
    })


@router.post("/race")
async def select_race(request: Request, race: str = Form(...)):
    """Process race selection."""
    session = get_session(request)
    races = get_races()

    if race not in races:
        return RedirectResponse("/character/new", status_code=303)

    session.character_creation.race = race
    save_session(request, session)

    return RedirectResponse("/character/class", status_code=303)


@router.get("/class", response_class=HTMLResponse)
async def select_class_page(request: Request):
    """Show class selection page."""
    session = get_session(request)

    if not session.character_creation.race:
        return RedirectResponse("/character/new", status_code=303)

    classes = get_classes()

    # Format class data for display
    class_list = []
    for class_name, props in classes.items():
        class_list.append({
            "name": class_name,
            "hit_die": props["hit_die"],
            "primary_ability": props["primary_ability"],
            "saving_throws": ", ".join(props["saving_throw_proficiencies"]),
            "num_skills": props["num_skill_choices"],
            "armor": ", ".join(props["armor_training"]) if props["armor_training"] else "None",
            "weapons": ", ".join(props["weapon_proficiencies"][:3]) + ("..." if len(props["weapon_proficiencies"]) > 3 else "")
        })

    return templates.TemplateResponse("character/select_class.html", {
        "request": request,
        "title": "Choose Your Class",
        "race": session.character_creation.race,
        "classes": class_list
    })


@router.post("/class")
async def select_class(request: Request, class_name: str = Form(...)):
    """Process class selection."""
    session = get_session(request)
    classes = get_classes()

    if class_name not in classes:
        return RedirectResponse("/character/class", status_code=303)

    session.character_creation.class_name = class_name
    save_session(request, session)

    return RedirectResponse("/character/details", status_code=303)


@router.get("/details", response_class=HTMLResponse)
async def details_page(request: Request):
    """Show name and weapon selection page."""
    session = get_session(request)

    if not session.character_creation.race or not session.character_creation.class_name:
        return RedirectResponse("/character/new", status_code=303)

    classes = get_classes()
    class_props = classes[session.character_creation.class_name]

    # Get available weapons based on class proficiencies
    all_weapons = get_all_weapons_flat()
    available_weapons = []

    weapon_proficiencies = class_props["weapon_proficiencies"]

    for weapon_name, weapon_data in all_weapons.items():
        # Check if class can use this weapon
        can_use = False
        if "Simple" in weapon_proficiencies and weapon_data["category"] == "Simple":
            can_use = True
        elif "Martial" in weapon_proficiencies and weapon_data["category"] == "Martial":
            can_use = True
        elif weapon_name in weapon_proficiencies:
            can_use = True

        if can_use:
            available_weapons.append({
                "name": weapon_name,
                "damage_die": weapon_data["damage_die"],
                "damage_type": weapon_data["damage_type"],
                "category": weapon_data["category"],
                "properties": ", ".join(weapon_data.get("properties", [])) or "None",
                "description": weapon_data.get("description", "")
            })

    # Get available armors based on class armor training
    all_armors = get_all_armors_flat()
    armor_training = class_props["armor_training"]
    available_armors = []

    for armor_name, armor_data in all_armors.items():
        if armor_data["category"] in armor_training:
            available_armors.append({
                "name": armor_name,
                "base_ac": armor_data["base_ac"],
                "category": armor_data["category"],
                "weight": armor_data["weight"],
                "stealth_disadvantage": armor_data["stealth_disadvantage"],
            })

    # Get skill choices for this class
    skill_choices = class_props["skill_proficiency_choices"]
    num_skills = class_props["num_skill_choices"]

    return templates.TemplateResponse("character/details.html", {
        "request": request,
        "title": "Character Details",
        "race": session.character_creation.race,
        "class_name": session.character_creation.class_name,
        "weapons": available_weapons,
        "armors": available_armors,
        "skill_choices": skill_choices,
        "num_skills": num_skills
    })


@router.post("/create")
async def create_character(
    request: Request,
    name: str = Form(...),
    weapon: str = Form(...),
    armor: str = Form(default=""),
    skills: list = Form(default=[])
):
    """Finalize character creation."""
    session = get_session(request)

    if not session.character_creation.race or not session.character_creation.class_name:
        return RedirectResponse("/character/new", status_code=303)

    # Create character using factory
    factory = CharacterFactory()
    character = factory.create_character(
        name=name,
        race=session.character_creation.race,
        class_name=session.character_creation.class_name
    )

    # Equip weapon
    weapon_factory = WeaponFactory()
    try:
        weapon_obj = weapon_factory.get_weapon_by_name(weapon)
        character.equip_weapon(weapon_obj, WeaponSlot.MAIN_HAND)
    except ValueError:
        pass  # Invalid weapon, skip

    # Equip armor
    if armor:
        armor_factory = ArmorFactory()
        try:
            armor_obj = armor_factory.get_armor_by_name(armor)
            character.equip(armor_obj)
        except ValueError:
            pass  # Invalid armor, skip

    # Add skill proficiencies
    if isinstance(skills, str):
        skills = [skills]
    for skill in skills:
        character.add_skill_proficiency(skill)

    # Add starting gold and items
    character.gold = 25
    character.add_item(HealingPotion("Small Healing Potion", 10))
    character.add_item(HealingPotion("Medium Healing Potion", 25))

    # Save character to session
    session.character = character
    session.character_creation.name = name
    session.character_creation.weapon = weapon
    session.character_creation.armor = armor if armor else None
    session.character_creation.skills = skills

    # Initialize campaign
    campaign = get_campaign()
    session.act = campaign["acts"][0]
    session.current_location = session.act["locations"][0]
    if session.current_location.get("areas"):
        session.current_area = session.current_location["areas"][0]

    save_session(request, session)

    return RedirectResponse("/character/summary", status_code=303)


@router.get("/summary", response_class=HTMLResponse)
async def character_summary(request: Request):
    """Display created character summary."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    char_data = session._serialize_character()

    return templates.TemplateResponse("character/summary.html", {
        "request": request,
        "title": f"{char_data['name']} - Character Summary",
        "character": char_data
    })
