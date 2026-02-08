import sys
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session, get_classes
from character import WeaponSlot
from equipmentType import EquipmentType
from weapon import Weapon
from armor import Armor

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def _can_equip_item(item, weapon_proficiencies, armor_training):
    """Check if the character is proficient with an inventory item."""
    if isinstance(item, Weapon):
        return item.category in weapon_proficiencies or item.name in weapon_proficiencies
    if isinstance(item, Armor):
        return item.category in armor_training
    return False


@router.get("/", response_class=HTMLResponse)
async def inventory_view(request: Request):
    """Inventory and equipment management page."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    char_data = session._serialize_character()

    # Look up class proficiencies
    classes = get_classes()
    class_props = classes.get(session.character_creation.class_name, {})
    weapon_proficiencies = class_props.get("weapon_proficiencies", [])
    armor_training = class_props.get("armor_training", [])

    # Annotate inventory items with can_equip
    for i, item in enumerate(char_data["inventory"]):
        actual_item = session.character.inventory[i]
        item["can_equip"] = _can_equip_item(actual_item, weapon_proficiencies, armor_training)
        item["index"] = i

    message = request.session.pop("inventory_message", None)
    error = request.session.pop("inventory_error", None)

    return templates.TemplateResponse("inventory/index.html", {
        "request": request,
        "title": "Inventory",
        "character": char_data,
        "message": message,
        "error": error,
    })


@router.post("/equip-weapon")
async def equip_weapon(request: Request, item_index: int = Form(...)):
    """Equip a weapon from inventory."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    character = session.character
    if item_index < 0 or item_index >= len(character.inventory):
        request.session["inventory_error"] = "Invalid item."
        return RedirectResponse("/inventory", status_code=303)

    item = character.inventory[item_index]
    if not isinstance(item, Weapon):
        request.session["inventory_error"] = "That item is not a weapon."
        return RedirectResponse("/inventory", status_code=303)

    # Check proficiency
    classes = get_classes()
    class_props = classes.get(session.character_creation.class_name, {})
    weapon_proficiencies = class_props.get("weapon_proficiencies", [])
    if item.category not in weapon_proficiencies and item.name not in weapon_proficiencies:
        request.session["inventory_error"] = f"You are not proficient with {item.name}."
        return RedirectResponse("/inventory", status_code=303)

    # equip_weapon handles inventory (removes new from inventory, returns old to inventory)
    character.equip_weapon(item, WeaponSlot.MAIN_HAND)
    session.character_creation.weapon = item.name

    request.session["inventory_message"] = f"Equipped {item.name}."
    save_session(request, session)
    return RedirectResponse("/inventory", status_code=303)


@router.post("/unequip-weapon")
async def unequip_weapon(request: Request):
    """Unequip the main hand weapon."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    character = session.character
    weapon = character.weapon_slots.get(WeaponSlot.MAIN_HAND)
    if not weapon:
        request.session["inventory_error"] = "No weapon equipped."
        return RedirectResponse("/inventory", status_code=303)

    # unequip_weapon handles inventory (adds weapon back to inventory)
    character.unequip_weapon(WeaponSlot.MAIN_HAND)
    session.character_creation.weapon = None

    request.session["inventory_message"] = f"Unequipped {weapon.name}."
    save_session(request, session)
    return RedirectResponse("/inventory", status_code=303)


@router.post("/equip-armor")
async def equip_armor(request: Request, item_index: int = Form(...)):
    """Equip armor from inventory."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    character = session.character
    if item_index < 0 or item_index >= len(character.inventory):
        request.session["inventory_error"] = "Invalid item."
        return RedirectResponse("/inventory", status_code=303)

    item = character.inventory[item_index]
    if not isinstance(item, Armor):
        request.session["inventory_error"] = "That item is not armor."
        return RedirectResponse("/inventory", status_code=303)

    # Check proficiency
    classes = get_classes()
    class_props = classes.get(session.character_creation.class_name, {})
    armor_training = class_props.get("armor_training", [])
    if item.category not in armor_training:
        request.session["inventory_error"] = f"You are not trained with {item.name}."
        return RedirectResponse("/inventory", status_code=303)

    # entity.equip() does NOT manage inventory, so handle manually
    old_armor = character.equipment.get(EquipmentType.ARMOR)
    character.inventory.remove(item)
    if old_armor:
        character.inventory.append(old_armor)
    character.equip(item)
    session.character_creation.armor = item.name

    request.session["inventory_message"] = f"Equipped {item.name}."
    save_session(request, session)
    return RedirectResponse("/inventory", status_code=303)


@router.post("/unequip-armor")
async def unequip_armor(request: Request):
    """Unequip current armor."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    character = session.character
    armor = character.equipment.get(EquipmentType.ARMOR)
    if not armor:
        request.session["inventory_error"] = "No armor equipped."
        return RedirectResponse("/inventory", status_code=303)

    # Manually add armor back to inventory, then unequip
    character.inventory.append(armor)
    character.unequip(EquipmentType.ARMOR)
    session.character_creation.armor = None

    request.session["inventory_message"] = f"Unequipped {armor.name}."
    save_session(request, session)
    return RedirectResponse("/inventory", status_code=303)
