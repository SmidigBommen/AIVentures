import sys
import random
from pathlib import Path
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session, get_all_weapons_flat, get_all_armors_flat, get_quests, get_shopkeeper, get_default_shop_inventory
from web.dependencies import require_character
from items import HealingPotion, QuestItem
from weapon import Weapon
from armor import Armor
from skills import make_skill_check
from engine.quests import turn_in_quest as engine_turn_in_quest

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

def get_shopkeeper_dialog(context: str, character_gold: int = 0) -> str:
    """Get a context-appropriate shopkeeper dialog line."""
    shopkeeper = get_shopkeeper()
    if context in shopkeeper:
        return random.choice(shopkeeper[context])
    if context == "buy":
        return random.choice(shopkeeper["buy_reactions"])
    elif context == "sell":
        return random.choice(shopkeeper["sell_reactions"])
    elif context == "low_gold" or character_gold <= 5:
        return random.choice(shopkeeper["low_gold"])
    elif context == "greeting":
        return random.choice(shopkeeper["greetings"])
    elif context == "farewell":
        return random.choice(shopkeeper["farewell"])
    else:
        return random.choice(shopkeeper["browse"])


def get_shop_inventory(session):
    """Get shop inventory from session, initializing if needed."""
    if session.shop_inventory is None:
        session.shop_inventory = [
            {**item, "quantity": 5} for item in get_default_shop_inventory()
        ]
    return session.shop_inventory


def restock_shop(session):
    """Reset all shop items to full stock (quantity 5) and clear haggle state."""
    session.shop_inventory = [
        {**item, "quantity": 5} for item in get_default_shop_inventory()
    ]
    session.haggled_items = {}


def get_effective_price(base_price, item_index, haggle_state):
    """Get the effective price for an item after any haggle discount."""
    key = str(item_index)
    if key in haggle_state:
        discount = haggle_state[key]
        return max(1, int(base_price * (1 - discount / 100)))
    return base_price


@router.get("/", response_class=HTMLResponse)
async def shop_view(request: Request, session=Depends(require_character)):
    """Shop view - show items for sale."""

    # Check if shop is available in current area
    area = session.current_area
    special = area.get("special", "") if area else ""
    has_shop = "shop" in str(special).lower() or "market" in str(special).lower()
    if not area or not has_shop:
        return RedirectResponse("/game", status_code=303)

    char_data = session._serialize_character()
    inventory = get_shop_inventory(session)
    haggle_state = session.haggled_items

    # Build inventory with effective prices
    shop_items = []
    for i, item in enumerate(inventory):
        effective_price = get_effective_price(item["price"], i, haggle_state)
        haggled = str(i) in haggle_state
        discount = haggle_state.get(str(i), 0)
        shop_items.append({
            **item,
            "effective_price": effective_price,
            "original_price": item["price"],
            "haggled": haggled,
            "discount": discount,
        })

    # Get player's sellable items (exclude quest items)
    sellable_items = []
    for i, item in enumerate(session.character.inventory):
        if isinstance(item, QuestItem):
            continue
        sell_price = calculate_sell_price(item, inventory)
        sellable_items.append({
            "index": i,
            "name": item.name,
            "description": item.description if hasattr(item, 'description') else "",
            "sell_price": sell_price
        })

    # Build quest data
    all_quests = get_quests()
    current_act = session.act.get("number", 1) if session.act else 1

    # Active quests with full details
    active_quest_list = []
    for quest_id, quest_state in session.active_quests.items():
        quest_def = all_quests.get(quest_id)
        if quest_def:
            progress_pct = min(100, int(quest_state["progress"] / quest_def["target_count"] * 100))
            active_quest_list.append({
                "id": quest_id,
                "name": quest_def["name"],
                "description": quest_def["description"],
                "type": quest_def["type"],
                "target_monster": quest_def["target_monster"],
                "target_count": quest_def["target_count"],
                "progress": quest_state["progress"],
                "progress_pct": progress_pct,
                "status": quest_state["status"],
                "rewards": quest_def["rewards"],
            })

    # Available quests (for current act, not active, not completed)
    available_quest_list = []
    for quest_id, quest_def in all_quests.items():
        if quest_def["act"] <= current_act and quest_id not in session.active_quests and quest_id not in session.completed_quests:
            available_quest_list.append({
                "id": quest_id,
                "name": quest_def["name"],
                "description": quest_def["description"],
                "type": quest_def["type"],
                "target_monster": quest_def["target_monster"],
                "target_count": quest_def["target_count"],
                "rewards": quest_def["rewards"],
                "dialog_offer": quest_def["dialog_offer"],
            })

    # Check for flash messages and determine dialog context
    message = session.pop_flash("shop_message")
    error = session.pop_flash("shop_error")
    dialog_context = session.pop_flash("shop_dialog_context") or "greeting"
    haggle_result = session.haggle_result
    session.haggle_result = None  # Clear after reading
    active_tab = request.query_params.get("tab", "wares")

    dialog = get_shopkeeper_dialog(dialog_context, session.character.gold)

    # Save to persist flash pops and haggle_result clear
    save_session(request, session)

    return templates.TemplateResponse("shop/index.html", {
        "request": request,
        "title": "Shop",
        "character": char_data,
        "shop_items": shop_items,
        "sellable_items": sellable_items,
        "message": message,
        "error": error,
        "shopkeeper": get_shopkeeper(),
        "dialog": dialog,
        "haggle_result": haggle_result,
        "active_quests": active_quest_list,
        "available_quests": available_quest_list,
        "active_tab": active_tab,
        "quest_slots_full": len(session.active_quests) >= 3,
    })


def calculate_sell_price(item, shop_inventory):
    """Calculate sell price for an item (50% of buy price)."""
    for shop_item in shop_inventory:
        if item.name == shop_item["name"]:
            return max(1, shop_item["price"] // 2)

    if isinstance(item, HealingPotion):
        return max(1, item.healing_amount // 2)

    if isinstance(item, Weapon):
        all_weapons = get_all_weapons_flat()
        if item.name in all_weapons:
            return max(1, int(all_weapons[item.name].get("cost_gp", 1)) // 2)

    if isinstance(item, Armor):
        all_armors = get_all_armors_flat()
        if item.name in all_armors:
            return max(1, int(all_armors[item.name].get("cost_gp", 1)) // 2)

    return 1


@router.post("/buy")
async def buy_item(request: Request, item_index: int = Form(...), session=Depends(require_character)):
    """Purchase an item from the shop."""

    inventory = get_shop_inventory(session)

    if 0 <= item_index < len(inventory):
        item = inventory[item_index]
        effective_price = get_effective_price(item["price"], item_index, session.haggled_items)

        if item["quantity"] <= 0:
            session.set_flash("shop_error", f"{item['name']} is out of stock!")
            save_session(request, session)
            return RedirectResponse("/shop", status_code=303)

        if session.character.gold < effective_price:
            session.set_flash("shop_error", f"Not enough gold! You need {effective_price} gold.")
            save_session(request, session)
            return RedirectResponse("/shop", status_code=303)

        session.character.gold -= effective_price
        item["quantity"] -= 1

        new_item = HealingPotion(item["name"], item["healing"])
        session.character.add_item(new_item)

        session.set_flash("shop_message", f"Purchased {item['name']} for {effective_price} gold!")
        session.set_flash("shop_dialog_context", "buy")
        save_session(request, session)
    else:
        session.set_flash("shop_error", "Invalid item selection.")
        save_session(request, session)

    return RedirectResponse("/shop", status_code=303)


@router.post("/sell")
async def sell_item(request: Request, item_index: int = Form(...), session=Depends(require_character)):
    """Sell an item to the shop."""

    if 0 <= item_index < len(session.character.inventory):
        item = session.character.inventory[item_index]
        inventory = get_shop_inventory(session)

        sell_price = calculate_sell_price(item, inventory)

        session.character.gold += sell_price
        item_name = item.name
        session.character.inventory.pop(item_index)

        session.set_flash("shop_message", f"Sold {item_name} for {sell_price} gold!")
        session.set_flash("shop_dialog_context", "sell")
        save_session(request, session)
    else:
        session.set_flash("shop_error", "Invalid item selection.")
        save_session(request, session)

    return RedirectResponse("/shop", status_code=303)


@router.post("/haggle")
async def haggle_item(request: Request, item_index: int = Form(...), session=Depends(require_character)):
    """Attempt to haggle the price of an item using a Persuasion check."""

    inventory = get_shop_inventory(session)
    haggle_state = session.haggled_items

    if not (0 <= item_index < len(inventory)):
        session.set_flash("shop_error", "Invalid item selection.")
        save_session(request, session)
        return RedirectResponse("/shop", status_code=303)

    key = str(item_index)
    if key in haggle_state:
        session.set_flash("shop_error", "You've already haggled over this item!")
        session.set_flash("shop_dialog_context", "browse")
        save_session(request, session)
        return RedirectResponse("/shop", status_code=303)

    item = inventory[item_index]

    result = make_skill_check(session.character, "Persuasion", difficulty_class=10)
    roll = result["roll"]
    total = result["total"]
    modifier = result["modifier"]

    if roll == 20:
        discount = 40
        dialog_key = "haggle_nat20"
        tier = "nat20"
    elif total >= 20:
        discount = 25
        dialog_key = "haggle_great"
        tier = "great"
    elif total >= 16:
        discount = 15
        dialog_key = "haggle_good"
        tier = "good"
    elif total >= 12:
        discount = 10
        dialog_key = "haggle_okay"
        tier = "okay"
    elif roll == 1:
        discount = -25
        dialog_key = "haggle_nat1"
        tier = "nat1"
    else:
        discount = 0
        dialog_key = "haggle_fail"
        tier = "fail"

    haggle_state[key] = discount

    effective_price = get_effective_price(item["price"], item_index, haggle_state)

    session.haggle_result = {
        "roll": roll,
        "modifier": modifier,
        "total": total,
        "discount": discount,
        "tier": tier,
        "item_name": item["name"],
        "original_price": item["price"],
        "new_price": effective_price,
    }
    session.set_flash("shop_dialog_context", dialog_key)
    save_session(request, session)

    return RedirectResponse("/shop", status_code=303)


@router.post("/quest/accept")
async def accept_quest(request: Request, quest_id: str = Form(...), session=Depends(require_character)):
    """Accept a quest from the quest board."""

    all_quests = get_quests()
    quest_def = all_quests.get(quest_id)

    if not quest_def:
        session.set_flash("shop_error", "Unknown quest.")
        save_session(request, session)
        return RedirectResponse("/shop?tab=quests", status_code=303)

    if len(session.active_quests) >= 3:
        session.set_flash("shop_error", "You can only have 3 active quests!")
        session.set_flash("shop_dialog_context", "quest_full")
        save_session(request, session)
        return RedirectResponse("/shop?tab=quests", status_code=303)

    if quest_id in session.active_quests or quest_id in session.completed_quests:
        session.set_flash("shop_error", "Quest already accepted or completed.")
        save_session(request, session)
        return RedirectResponse("/shop?tab=quests", status_code=303)

    session.active_quests[quest_id] = {"progress": 0, "status": "active"}
    session.set_flash("shop_message", f"Quest accepted: {quest_def['name']}")
    session.set_flash("shop_dialog_context", "quest_accept")
    save_session(request, session)

    return RedirectResponse("/shop?tab=quests", status_code=303)


@router.post("/quest/turn-in")
async def turn_in_quest_route(request: Request, quest_id: str = Form(...), session=Depends(require_character)):
    """Turn in a completed quest for rewards."""

    all_quests = get_quests()

    result = engine_turn_in_quest(
        quest_id, session.active_quests, session.completed_quests,
        all_quests, session.character)

    if not result:
        session.set_flash("shop_error", "Quest not ready for turn-in.")
        save_session(request, session)
        return RedirectResponse("/shop?tab=quests", status_code=303)

    session.set_flash("shop_message",
        f"Quest complete: {result['quest_name']}! +{result['gold']} gold, +{result['xp']} XP")
    session.set_flash("shop_dialog_context", "quest_complete")
    save_session(request, session)

    return RedirectResponse("/shop?tab=quests", status_code=303)


@router.post("/quest/abandon")
async def abandon_quest(request: Request, quest_id: str = Form(...), session=Depends(require_character)):
    """Abandon an active quest."""

    all_quests = get_quests()
    quest_def = all_quests.get(quest_id)

    if quest_id not in session.active_quests:
        session.set_flash("shop_error", "Quest not found in your active quests.")
        save_session(request, session)
        return RedirectResponse("/shop?tab=quests", status_code=303)

    if quest_def and quest_def["type"] == "gather":
        session.character.inventory = [
            item for item in session.character.inventory
            if not (isinstance(item, QuestItem) and item.quest_id == quest_id)
        ]

    del session.active_quests[quest_id]

    quest_name = quest_def["name"] if quest_def else "Unknown"
    session.set_flash("shop_message", f"Quest abandoned: {quest_name}")
    session.set_flash("shop_dialog_context", "quest_abandon")
    save_session(request, session)

    return RedirectResponse("/shop?tab=quests", status_code=303)
