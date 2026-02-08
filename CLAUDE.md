# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIVentures is a D&D 5e-inspired text adventure game built in Python. It has two interfaces:
- **CLI** (`main.py`): Terminal-based game using `input()`/`print()` with ANSI colors
- **Web UI** (`web/`): FastAPI + Jinja2 server-rendered HTML interface (the active development focus)

## Commands

### Run the web app
```bash
pip install -r requirements.txt
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
```

### Run tests
```bash
pytest                          # all tests
pytest test/test_battle.py      # single test file
pytest -k "test_name"           # single test by name
```

### Run the CLI game
```bash
python main.py
```

## Architecture

### Domain Model (root-level `.py` files)

The game uses a D&D 5e rules engine with an `Entity` base class:

- **`Entity`** → base class with ability scores (STR/DEX/CON/INT/WIS/CHA), modifiers, AC calculation (light/medium/heavy armor rules), skill checks, saving throws, proficiency bonus, and equipment slots (`EquipmentType` enum)
- **`Character(Entity)`** → player: weapon slots (`WeaponSlot.MAIN_HAND`/`OFF_HAND`), inventory, XP/leveling, hit die, gold, healing potions
- **`Monster(Entity)`** → enemy: created by `MonsterFactory`, has a single `weapon` attribute (not slots)
- **`Weapon(Equipment)`** → damage_die, damage_dice_count, damage_type, category (Simple/Martial), properties (finesse, ammunition determine attack modifier)
- **`Armor(Equipment)`** → base_ac, category (Light/Medium/Heavy), affects AC calculation differently per category

### Factory Pattern

All entity/item creation goes through factories that read from `json/` data files:
- **`CharacterFactory`** → reads `races.json`, `races_default_values.json`, `classes_properties.json`. Call: `factory.create_character(name, race, class_name)`
- **`MonsterFactory`** → reads `monster_default_values.json`. Call: `factory.create_monster(name, race, class_name, level, weapon_name)`
- **`WeaponFactory`** → reads `weapon-catalog.json`. Call: `factory.get_weapon_by_name(name)`
- **`ArmorFactory`** → reads `armor_catalog.json`. Call: `factory.get_armor_by_name(name)`
- **`LootGenerator`** → tier-based loot drops (potion/gold/weapon/armor) with weighted chances

### Battle System

Two separate battle implementations exist:
- **`battleAI.py` (`Battle` class)** → CLI version, interactive `input()` turns, used by `main.py`
- **`web/routes/battle.py`** → Web version, reimplements combat via HTTP POST endpoints, monster state stored in `BattleState` dataclass (not a `Monster` object)

Combat mechanics: d20 attack roll + ability modifier + proficiency vs AC. Weapon properties (`finesse`, `ammunition`) determine which ability modifier to use. Monster AI: 70% attack, 30% defend.

### Web Application (`web/`)

- **`web/app.py`** → FastAPI app, mounts static files, includes route blueprints at `/character`, `/game`, `/battle`, `/shop`
- **`web/game_session.py`** → `GameSession` dataclass serialized to/from Starlette session cookies. Contains `CharacterCreationState`, `BattleState`, and references to campaign location/area data. Character objects are recreated from factory on each request via `_restore_character()`.
- **Routes** use server-side rendering with Jinja2 templates and POST/Redirect/GET pattern (303 redirects)
- **Templates** in `web/templates/` extend `base.html`
- **Session state**: Game state is stored in signed cookies via `SessionMiddleware`. The `GameSession` serializes the full character + battle state to a dict, storing only location/area IDs (resolved against `campaign.json` on restore).

### Game World (`json/campaign.json`)

Campaign data defines acts → locations → areas. Each area has `connections` (list of area IDs for navigation), `encounters` (0-10 rating for encounter chance), `monster_types`, and optional `special` strings (e.g., "shop", "inn" which enable shop/rest features in the web UI).

### Key Design Patterns

- Factories load JSON config once and create domain objects
- Ability modifiers derived as `(score - 10) // 2` everywhere
- `sys.path.insert(0, ...)` used in web modules to import root-level game modules
- Web battle stores monster stats as flat fields in `BattleState` (not a `Monster` object) to enable cookie serialization
- Shop restocks after 10 monster kills or player death
