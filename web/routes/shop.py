import sys
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session
from items import HealingPotion

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Shop inventory - shared across sessions but quantity per session
DEFAULT_SHOP_INVENTORY = [
    {"name": "Minor Healing Potion", "healing": 5, "price": 10, "description": "Restores 5 HP"},
    {"name": "Healing Potion", "healing": 10, "price": 25, "description": "Restores 10 HP"},
    {"name": "Greater Healing Potion", "healing": 20, "price": 50, "description": "Restores 20 HP"},
]


def get_shop_inventory(request):
    """Get shop inventory from session, initializing if needed."""
    if "shop_inventory" not in request.session:
        request.session["shop_inventory"] = [
            {**item, "quantity": 5} for item in DEFAULT_SHOP_INVENTORY
        ]
    return request.session["shop_inventory"]


@router.get("/", response_class=HTMLResponse)
async def shop_view(request: Request):
    """Shop view - show items for sale."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    # Check if shop is available in current area
    area = session.current_area
    special = area.get("special", "") if area else ""
    has_shop = "shop" in str(special).lower() or "market" in str(special).lower()
    if not area or not has_shop:
        return RedirectResponse("/game", status_code=303)

    char_data = session._serialize_character()
    inventory = get_shop_inventory(request)

    # Get player's sellable items
    sellable_items = []
    for i, item in enumerate(session.character.inventory):
        sell_price = calculate_sell_price(item, inventory)
        sellable_items.append({
            "index": i,
            "name": item.name,
            "description": item.description if hasattr(item, 'description') else "",
            "sell_price": sell_price
        })

    # Check for messages
    message = request.session.pop("shop_message", None)
    error = request.session.pop("shop_error", None)

    return templates.TemplateResponse("shop/index.html", {
        "request": request,
        "title": "Shop",
        "character": char_data,
        "shop_inventory": inventory,
        "sellable_items": sellable_items,
        "message": message,
        "error": error
    })


def calculate_sell_price(item, shop_inventory):
    """Calculate sell price for an item (50% of buy price)."""
    for shop_item in shop_inventory:
        if item.name == shop_item["name"]:
            return max(1, shop_item["price"] // 2)

    # Default pricing for items not in shop
    if isinstance(item, HealingPotion):
        return max(1, item.healing_amount // 2)
    return 1


@router.post("/buy")
async def buy_item(request: Request, item_index: int = Form(...)):
    """Purchase an item from the shop."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    inventory = get_shop_inventory(request)

    if 0 <= item_index < len(inventory):
        item = inventory[item_index]

        # Check stock
        if item["quantity"] <= 0:
            request.session["shop_error"] = f"{item['name']} is out of stock!"
            return RedirectResponse("/shop", status_code=303)

        # Check gold
        if session.character.gold < item["price"]:
            request.session["shop_error"] = f"Not enough gold! You need {item['price']} gold."
            return RedirectResponse("/shop", status_code=303)

        # Process purchase
        session.character.gold -= item["price"]
        item["quantity"] -= 1

        # Add item to character inventory
        new_item = HealingPotion(item["name"], item["healing"])
        session.character.add_item(new_item)

        request.session["shop_message"] = f"Purchased {item['name']} for {item['price']} gold!"
        save_session(request, session)
    else:
        request.session["shop_error"] = "Invalid item selection."

    return RedirectResponse("/shop", status_code=303)


@router.post("/sell")
async def sell_item(request: Request, item_index: int = Form(...)):
    """Sell an item to the shop."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    if 0 <= item_index < len(session.character.inventory):
        item = session.character.inventory[item_index]
        inventory = get_shop_inventory(request)

        # Calculate sell price
        sell_price = calculate_sell_price(item, inventory)

        # Process sale
        session.character.gold += sell_price
        item_name = item.name
        session.character.inventory.pop(item_index)

        request.session["shop_message"] = f"Sold {item_name} for {sell_price} gold!"
        save_session(request, session)
    else:
        request.session["shop_error"] = "Invalid item selection."

    return RedirectResponse("/shop", status_code=303)
