"""FastAPI dependencies for common route guards."""

from fastapi import Request
from fastapi.responses import RedirectResponse

from web.game_session import get_session, GameSession


async def get_game_session(request: Request) -> GameSession:
    """Load the game session from the request."""
    return get_session(request)


class RequireCharacter:
    """Dependency that ensures a character exists, otherwise redirects."""

    async def __call__(self, request: Request) -> GameSession:
        session = get_session(request)
        if not session.character:
            raise _RedirectException("/character/new")
        return session


class RequireBattle:
    """Dependency that ensures an active battle exists."""

    async def __call__(self, request: Request) -> GameSession:
        session = get_session(request)
        if not session.character:
            raise _RedirectException("/character/new")
        if not session.battle.is_active:
            raise _RedirectException("/game")
        return session


class _RedirectException(Exception):
    """Internal exception for dependency redirects."""
    def __init__(self, url: str):
        self.url = url


def add_redirect_handler(app):
    """Register the exception handler on the FastAPI app."""
    @app.exception_handler(_RedirectException)
    async def redirect_handler(request: Request, exc: _RedirectException):
        return RedirectResponse(exc.url, status_code=303)


# Singleton instances for use as dependencies
require_character = RequireCharacter()
require_battle = RequireBattle()
