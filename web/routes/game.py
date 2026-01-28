import sys
import random
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session, get_campaign

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def game_view(request: Request):
    """Main game view - show current location."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    # Check if in battle
    if session.battle.is_active:
        return RedirectResponse("/battle", status_code=303)

    char_data = session._serialize_character()
    location = session.current_location
    area = session.current_area

    # Get connected areas
    connected_areas = []
    if area and "connections" in area:
        for conn_id in area["connections"]:
            for a in location.get("areas", []):
                if a["id"] == conn_id:
                    connected_areas.append(a)
                    break

    # Check if shop is available (special can be a string like "shop_location")
    special = area.get("special", "") if area else ""
    has_shop = "shop" in str(special).lower()

    # Check if rest is available
    can_rest = "rest" in str(special).lower() or "inn" in str(special).lower() or "tavern" in str(special).lower()

    return templates.TemplateResponse("game/location.html", {
        "request": request,
        "title": f"{location['name']} - {area['name']}" if area else location["name"],
        "character": char_data,
        "location": location,
        "area": area,
        "connected_areas": connected_areas,
        "has_shop": has_shop,
        "can_rest": can_rest,
        "act": session.act
    })


@router.post("/move")
async def move_to_area(request: Request, area_id: str = Form(...)):
    """Move to a connected area."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    location = session.current_location
    current_area = session.current_area

    # Verify the area is connected
    if current_area and area_id in current_area.get("connections", []):
        for area in location.get("areas", []):
            if area["id"] == area_id:
                session.current_area = area
                save_session(request, session)
                break

    return RedirectResponse("/game", status_code=303)


@router.post("/explore")
async def explore_area(request: Request):
    """Explore the current area - may trigger an encounter."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    area = session.current_area
    if not area:
        return RedirectResponse("/game", status_code=303)

    # Check for encounter based on area's encounter rating (0-10)
    encounter_chance = area.get("encounters", 5) / 10.0

    if random.random() < encounter_chance:
        # Start a battle
        return RedirectResponse("/battle/start", status_code=303)

    # No encounter - just update session with exploration result
    save_session(request, session)
    return RedirectResponse("/game?explored=true", status_code=303)


@router.post("/rest")
async def rest(request: Request):
    """Rest to recover HP."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    area = session.current_area
    special = area.get("special", "") if area else ""
    can_rest = "rest" in str(special).lower() or "inn" in str(special).lower() or "tavern" in str(special).lower()
    if not area or not can_rest:
        return RedirectResponse("/game", status_code=303)

    # Restore HP
    session.character.current_hit_points = session.character.max_hit_points
    save_session(request, session)

    return RedirectResponse("/game?rested=true", status_code=303)


@router.get("/travel", response_class=HTMLResponse)
async def travel_menu(request: Request):
    """Show available locations to travel to."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    act = session.act
    current_location = session.current_location

    # Filter out current location (use name as identifier since locations don't have id)
    available_locations = [loc for loc in act["locations"] if loc["name"] != current_location["name"]]

    char_data = session._serialize_character()

    return templates.TemplateResponse("game/travel.html", {
        "request": request,
        "title": "Travel",
        "character": char_data,
        "current_location": current_location,
        "locations": available_locations,
        "act": act
    })


@router.post("/travel")
async def travel_to_location(request: Request, location_name: str = Form(...)):
    """Travel to a different location."""
    session = get_session(request)

    if not session.character:
        return RedirectResponse("/character/new", status_code=303)

    act = session.act

    # Find the target location by name
    for location in act["locations"]:
        if location["name"] == location_name:
            session.current_location = location
            # Set to first area of new location
            if location.get("areas"):
                session.current_area = location["areas"][0]
            else:
                session.current_area = None
            save_session(request, session)
            break

    return RedirectResponse("/game", status_code=303)


@router.get("/status")
async def game_status(request: Request):
    """Get current game status as JSON."""
    session = get_session(request)

    if not session.character:
        return {"error": "No character"}

    char_data = session._serialize_character()

    return {
        "character": char_data,
        "location": session.current_location.get("name") if session.current_location else None,
        "area": session.current_area.get("name") if session.current_area else None,
        "in_battle": session.battle.is_active
    }
