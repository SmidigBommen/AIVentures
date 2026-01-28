import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

app = FastAPI(title="AIVentures", description="D&D 5e Text Adventure")

# Session middleware for tracking game state
app.add_middleware(SessionMiddleware, secret_key="aiventures-secret-key-change-in-production")

# Static files and templates
web_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=web_dir / "static"), name="static")
templates = Jinja2Templates(directory=web_dir / "templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with game start options."""
    return templates.TemplateResponse("base.html", {
        "request": request,
        "title": "AIVentures",
        "content": "home"
    })


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "game": "AIVentures"}


# Import and include routers
from web.routes import character, game, battle, shop

app.include_router(character.router, prefix="/character", tags=["character"])
app.include_router(game.router, prefix="/game", tags=["game"])
app.include_router(battle.router, prefix="/battle", tags=["battle"])
app.include_router(shop.router, prefix="/shop", tags=["shop"])
