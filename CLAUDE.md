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
- **`Character(Entity)`** → player: weapon slots (`WeaponSlot.MAIN_HAND`/`OFF_HAND`), inventory, XP/leveling, hit die, gold, healing potions, `power_points`/`max_power_points`/`active_effects` for the ability system
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

### Ability / Magic System

All 11 classes have unique abilities powered by **Power Points (PP)**:
- **Data**: `json/abilities.json` — 55 abilities (5 per class), each with cost, unlock_level, attack_method, damage/heal/effects
- **PP calculation** in `web/game_session.py`: `calculate_max_pp(class_name, level, primary_modifier)` — full casters get `level + mod`, half casters `level//2 + mod`, martial `level//3 + mod` (min 2)
- **Helpers** in `web/game_session.py`: `get_abilities()`, `get_class_abilities(class_name, level)`, `get_primary_modifier(character)`
- **Combat resolution** in `web/routes/battle.py`: `resolve_ability()` handles all attack methods (melee_attack, spell_attack, spell_save, auto_hit), damage, healing, and effect application
- **Active effects**: stored as lists on `BattleState` (`player_effects`, `monster_effects`). Each effect has `stat`, `value`, `duration`, `source`. Duration 0 = lasts entire combat, positive = rounds remaining. `tick_effects()` decrements each round. `get_effect_bonus(effects, stat)` sums bonuses.
- **Stat modifiers**: `ac`, `attack_bonus`, `damage_bonus`, `damage_reduction` — applied in weapon attacks, ability attacks, and monster turns
- PP initialized on character creation, restored on rest, recalculated on level up

### Battle System

Two separate battle implementations exist:
- **`battleAI.py` (`Battle` class)** → CLI version, interactive `input()` turns, used by `main.py`
- **`web/routes/battle.py`** → Web version, reimplements combat via HTTP POST endpoints, monster state stored in `BattleState` dataclass (not a `Monster` object)

Combat mechanics: d20 attack roll + ability modifier + proficiency vs AC. Weapon properties (`finesse`, `ammunition`) determine which ability modifier to use. Monster AI: 70% attack, 30% defend. Active effects from abilities modify attack/damage/AC/DR for both sides.

Battle actions: `POST /battle/attack`, `POST /battle/defend`, `POST /battle/ability` (with `ability_id` form field), `POST /battle/item`.

### Web Application (`web/`)

- **`web/app.py`** → FastAPI app, mounts static files, includes route blueprints at `/character`, `/game`, `/battle`, `/shop`, `/inventory`
- **`web/game_session.py`** → `GameSession` dataclass serialized to/from Starlette session cookies. Contains `CharacterCreationState`, `BattleState` (including `player_effects`/`monster_effects`), and references to campaign location/area data. Character objects are recreated from factory on each request via `_restore_character()`. Also contains ability system helpers.
- **Routes** use server-side rendering with Jinja2 templates and POST/Redirect/GET pattern (303 redirects)
- **Templates** in `web/templates/` extend `base.html` — all styling in `web/static/css/style.css`, all JS in `web/static/js/main.js` (no inline styles/scripts in templates)
- **Session state**: Game state is stored in signed cookies via `SessionMiddleware`. The `GameSession` serializes the full character + battle state to a dict, storing only location/area IDs (resolved against `campaign.json` on restore).

### UI Design System (`web/static/css/style.css`)

Consolidated CSS design system with:
- CSS custom properties for colors, spacing, typography, radii, shadows
- Cinzel font for headings (loaded from Google Fonts in `base.html`)
- Reusable components: `.glass`, `.panel`, `.btn-*`, `.selection-card`, `.stat-box`, `.health-bar`, `.toast`, `.steps` (step indicator), `.effect-badge`, `.btn-ability`/`.btn-ability-free`
- Battle arena uses glassmorphism with background image overlay
- Responsive breakpoints at 768px and 480px

### JavaScript (`web/static/js/main.js`)

- `SFX` object: Web Audio API synthesized sounds (hit, miss, heal, defend, spell, victory, defeat, levelup, coin, click)
- Toast notification system (`showToast`, `initToasts` — reads `data-toast` elements)
- Confetti effect (`showConfetti`) and screen shake (`screenShake`) triggered by `data-confetti`/`data-screen-shake` attributes
- Selection card handler, skill counter, battle log auto-scroll, health bar coloring, active nav link detection

### Game World (`json/campaign.json`)

Campaign data defines acts → locations → areas. Each area has `connections` (list of area IDs for navigation), `encounters` (0-10 rating for encounter chance), `monster_types`, and optional `special` strings (e.g., "shop", "inn" which enable shop/rest features in the web UI).

### Key Design Patterns

- Factories load JSON config once and create domain objects
- Ability modifiers derived as `(score - 10) // 2` everywhere
- `sys.path.insert(0, ...)` used in web modules to import root-level game modules
- Web battle stores monster stats as flat fields in `BattleState` (not a `Monster` object) to enable cookie serialization
- Shop restocks after 10 monster kills or player death
- All ability/spell data is JSON-driven (`json/abilities.json`) — no hardcoded spell logic
- Active effects are flat stat modifiers (`{stat, value, duration, source}`) applied per-round via `get_effect_bonus()`
