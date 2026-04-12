"""Save/Load manager — file I/O for intentional game saves.

Save files live in web/saves/, separate from the ephemeral web/sessions/ directory.
Each save wraps a GameSession.to_dict() snapshot with metadata for display.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from web.game_session import GameSession

SAVES_DIR = Path(__file__).parent / "saves"
MAX_SAVES = 10


def _save_file(save_id: str) -> Path:
    """Get the file path for a save. Sanitizes ID to prevent path traversal."""
    safe_id = "".join(c for c in save_id if c.isalnum() or c == "-")
    return SAVES_DIR / f"{safe_id}.json"


def _extract_metadata(session: GameSession) -> dict:
    """Pull display metadata from a session without full serialization overhead."""
    char_data = session.serialize_character()
    location_name = session.current_location.get("name") if session.current_location else "Unknown"
    return {
        "character_name": char_data["name"] if char_data else "Unknown",
        "character_level": char_data["level"] if char_data else 0,
        "character_class": char_data["class_name"] if char_data else "",
        "character_race": char_data["race"] if char_data else "",
        "location_name": location_name,
        "portrait": char_data.get("portrait", "") if char_data else "",
        "monster_kills": session.monster_kills,
    }


def get_save_count() -> int:
    """Return the number of save files on disk."""
    if not SAVES_DIR.exists():
        return 0
    return len(list(SAVES_DIR.glob("*.json")))


def list_saves() -> list[dict]:
    """Read all save files and return metadata, sorted by updated_at descending."""
    if not SAVES_DIR.exists():
        return []
    saves = []
    for path in SAVES_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            saves.append({
                "save_id": data["save_id"],
                "created_at": data["created_at"],
                "updated_at": data["updated_at"],
                "metadata": data["metadata"],
            })
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    saves.sort(key=lambda s: s["updated_at"], reverse=True)
    return saves


def create_save(session: GameSession) -> dict:
    """Create a new save file from the current session. Returns metadata."""
    SAVES_DIR.mkdir(exist_ok=True)
    save_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")
    metadata = _extract_metadata(session)

    session_data = session.to_dict()
    session_data["_flash"] = {}
    session_data["battle_rewards"] = None

    save_data = {
        "save_id": save_id,
        "created_at": now,
        "updated_at": now,
        "metadata": metadata,
        "session_data": session_data,
    }
    with open(_save_file(save_id), "w", encoding="utf-8") as f:
        json.dump(save_data, f)
    return save_data


def overwrite_save(save_id: str, session: GameSession) -> Optional[dict]:
    """Overwrite an existing save file, preserving created_at. Returns metadata or None."""
    path = _save_file(save_id)
    if not path.exists():
        return None

    try:
        with open(path, encoding="utf-8") as f:
            old_data = json.load(f)
        created_at = old_data["created_at"]
    except (json.JSONDecodeError, KeyError, OSError):
        created_at = datetime.now().isoformat(timespec="seconds")

    now = datetime.now().isoformat(timespec="seconds")
    metadata = _extract_metadata(session)

    session_data = session.to_dict()
    session_data["_flash"] = {}
    session_data["battle_rewards"] = None

    save_data = {
        "save_id": save_id,
        "created_at": created_at,
        "updated_at": now,
        "metadata": metadata,
        "session_data": session_data,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save_data, f)
    return save_data


def load_save(save_id: str) -> Optional[GameSession]:
    """Load a save file and return a GameSession with a fresh session_id."""
    path = _save_file(save_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        session_data = data["session_data"]
        session = GameSession.from_dict(session_data)
        session.session_id = str(uuid.uuid4())
        return session
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def delete_save(save_id: str) -> bool:
    """Delete a save file. Returns True if the file existed."""
    path = _save_file(save_id)
    if path.exists():
        path.unlink()
        return True
    return False


def get_save_metadata(save_id: str) -> Optional[dict]:
    """Read a single save and return only the metadata envelope."""
    path = _save_file(save_id)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {
            "save_id": data["save_id"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
            "metadata": data["metadata"],
        }
    except (json.JSONDecodeError, KeyError, OSError):
        return None
