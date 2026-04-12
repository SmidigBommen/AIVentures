import sys
from pathlib import Path
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from web.game_session import get_session, save_session
from web.save_manager import (
    list_saves, create_save, overwrite_save, load_save,
    delete_save, get_save_count, MAX_SAVES,
)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@router.get("/", response_class=HTMLResponse)
async def saves_view(request: Request):
    """Save/Load management page."""
    session = get_session(request)
    has_character = session.character is not None
    in_battle = session.battle.is_active

    can_save = has_character and not in_battle
    char_data = session.serialize_character() if has_character else None

    message = session.pop_flash("save_message")
    error = session.pop_flash("save_error")
    if message or error:
        save_session(request, session)

    return templates.TemplateResponse("saves/index.html", {
        "request": request,
        "title": "Save / Load Game",
        "character": char_data,
        "can_save": can_save,
        "in_battle": in_battle,
        "saves": list_saves(),
        "save_count": get_save_count(),
        "max_saves": MAX_SAVES,
        "message": message,
        "error": error,
    })


@router.post("/save")
async def create_new_save(request: Request):
    """Create a new save from the current session."""
    session = get_session(request)
    if not session.character:
        return RedirectResponse("/character/new", status_code=303)
    if session.battle.is_active:
        session.set_flash("save_error", "Cannot save during battle.")
        save_session(request, session)
        return RedirectResponse("/saves", status_code=303)
    if get_save_count() >= MAX_SAVES:
        session.set_flash("save_error", f"Maximum saves reached ({MAX_SAVES}). Delete an old save first.")
        save_session(request, session)
        return RedirectResponse("/saves", status_code=303)

    create_save(session)
    session.set_flash("save_message", "Game saved!")
    save_session(request, session)
    return RedirectResponse("/saves", status_code=303)


@router.post("/save/{save_id}")
async def overwrite_existing_save(request: Request, save_id: str):
    """Overwrite an existing save with the current session."""
    session = get_session(request)
    if not session.character:
        return RedirectResponse("/character/new", status_code=303)
    if session.battle.is_active:
        session.set_flash("save_error", "Cannot save during battle.")
        save_session(request, session)
        return RedirectResponse("/saves", status_code=303)

    result = overwrite_save(save_id, session)
    if result:
        session.set_flash("save_message", "Save updated!")
    else:
        session.set_flash("save_error", "Save not found.")
    save_session(request, session)
    return RedirectResponse("/saves", status_code=303)


@router.post("/load/{save_id}")
async def load_existing_save(request: Request, save_id: str):
    """Load a save file into the current session."""
    loaded = load_save(save_id)
    if not loaded:
        session = get_session(request)
        session.set_flash("save_error", "Could not load save. The file may be corrupted.")
        save_session(request, session)
        return RedirectResponse("/saves", status_code=303)

    loaded.set_flash("save_message", "Game loaded!")
    save_session(request, loaded)
    return RedirectResponse("/game", status_code=303)


@router.post("/delete/{save_id}")
async def delete_existing_save(request: Request, save_id: str):
    """Delete a save file."""
    session = get_session(request)
    if delete_save(save_id):
        session.set_flash("save_message", "Save deleted.")
    else:
        session.set_flash("save_error", "Save not found.")
    save_session(request, session)
    return RedirectResponse("/saves", status_code=303)
