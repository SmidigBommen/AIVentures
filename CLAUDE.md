# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIVentures is a D&D 5e-inspired text adventure game built in Python with a FastAPI + Jinja2 web interface.

## Commands

### Run the web app
```bash
pip install -r requirements.txt
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
```

### Run tests
```bash
pip install pytest httpx         # test deps (httpx only for test/test_web_flow.py)
pytest                          # all tests
pytest test/test_battle.py      # single test file
pytest -k "test_name"           # single test by name
```

### Screenshot every screen
```bash
python tools/ui_tour.py OUT_DIR --mobile      # all screens, desktop + 390px
python tools/ui_tour.py OUT_DIR --only battle,battle-hit,location
```
Plays a scripted game through the routes with a temp session folder and captures each screen with headless Chrome (flatpak by default, `--chrome` to override). Run it after changing templates or CSS. Key hints (`<kbd>`) are hidden in these captures because headless Chrome reports no hover.

## Architecture

### Domain Model (root-level `.py` files)

The game uses a D&D 5e rules engine with an `Entity` base class:

- **`Entity`** → base class with ability scores (STR/DEX/CON/INT/WIS/CHA), modifiers, AC calculation (light/medium/heavy armor rules), skill checks, saving throws, proficiency bonus, and equipment slots (`EquipmentType` enum)
- **`Character(Entity)`** → player: weapon slots (`WeaponSlot.MAIN_HAND`/`OFF_HAND`), inventory, XP/leveling, hit die, gold, healing potions, `power_points`/`max_power_points`/`active_effects` for the ability system
- **`Monster(Entity)`** → enemy: created by `MonsterFactory`, has a single `weapon` attribute (not slots)
- **`Weapon(Equipment)`** → damage_die, damage_dice_count, damage_type, category (Simple/Martial), properties (finesse, ammunition determine attack modifier)
- **`Armor(Equipment)`** → base_ac, category (Light/Medium/Heavy), affects AC calculation differently per category
- **`QuestItem(Item)`** → quest-specific item with `quest_id` field, `is_usable_in_battle=False`. Used for gather quests.

### Factory Pattern

All entity/item creation goes through factories that read from `json/` data files:
- **`CharacterFactory`** → reads `races.json`, `races_default_values.json`, `classes_properties.json`. Call: `factory.create_character(name, race, class_name)`
- **`MonsterFactory`** → reads `monster_default_values.json`. Call: `factory.create_monster(name, race, class_name, level, weapon_name)`
- **`WeaponFactory`** → reads `weapon-catalog.json`. Call: `factory.get_weapon_by_name(name)`
- **`ArmorFactory`** → reads `armor_catalog.json`. Call: `factory.get_armor_by_name(name)`
- **`LootGenerator`** → tier-based loot drops (potion/gold/weapon/armor) with weighted chances

### Game Engine (`engine/`)

Headless game logic shared across the application — no I/O, no web framework imports:

- **`engine/combat.py`** → `resolve_attack_roll()` (nat 20 crit / nat 1 miss), `resolve_weapon_attack()`, `resolve_flee()`, `get_weapon_attack_modifier()`, `roll_initiative()`, `calculate_xp_reward()`, `calculate_gold_reward()`
- **`engine/abilities.py`** → `resolve_player_ability()` — player class abilities (all attack methods, damage, healing, effects)
- **`engine/monster_ai.py`** → `choose_monster_action()`, `resolve_monster_ability()`, `tick_cooldowns()` — monster decisions and special abilities
- **`engine/effects.py`** → `get_effect_bonus()`, `tick_effects()`, `is_stunned()`, `resolve_round_conditions()`, `describe_effect()` — effect duration, stacking, conditions
- **`engine/leveling.py`** → `calculate_max_pp()`, `grant_xp()`, `asi_points_available()`, `improve_ability()`, `apply_ability_increases()` — power points; XP award with level-up HP and PP handling; Ability Score Improvements
- **`engine/campaign.py`** → `highest_unlocked_act()`, `is_act_complete()`, `get_area_boss()`, `collected_shards()`, `pending_ambush()` — pure progression rules derived from the defeated-boss list
- **`engine/events.py`** → `pick_event()`, `resolve_event_choice()`, `apply_outcome()` — exploration skill-check events
- **`engine/quests.py`** → `check_quest_progress()`, `turn_in_quest()` — quest state mutations after kills and turn-ins
- **`engine/combatant.py`** → `CombatantState`, `WeaponState` dataclasses — serializable battle state for monsters (replaces flat fields)

### Ability / Magic System

All 11 classes have unique abilities powered by **Power Points (PP)**:
- **Data**: `json/abilities.json` — 55 abilities (5 per class), each with cost, unlock_level, attack_method, damage/heal/effects
- **PP calculation** in `engine/leveling.py`: `calculate_max_pp(class_name, level, primary_modifier)` — full casters get `level + mod`, half casters and Monk `level//2 + mod`, martial `level//3 + mod` (min 2)
- **Scaling**: `scaling` (`{"level": {"dice_count": n}}`) applies to the damage dice, or to the heal dice of an ability with no damage. Every damage ability costing 2+ PP must scale (a test enforces it), otherwise the free abilities overtake it
- **`self_effects`**: effects an enemy-targeted ability puts on the player whether it hits or not (Reckless Attack: -3 AC for the round)
- **Display**: `summarize_ability(ability, level)` in `engine/abilities.py` returns the stat lines shown on the battle ability cards ("2d10 + mod slashing", "Self: damage bonus +2, whole fight")
- **Helpers** in `web/game_session.py`: `get_abilities()`, `get_class_abilities(class_name, level)`, `get_primary_modifier(character)`
- **Combat resolution** in `engine/abilities.py`: `resolve_player_ability()` handles all attack methods (melee_attack, spell_attack, spell_save, auto_hit), crits, damage, healing, and effect application. Enemy-targeted effects only apply if the ability lands (hit / failed save)
- **Active effects**: stored on `BattleState` (`player_effects`) and `CombatantState` (`effects`). Each effect has `stat`, `value`, `duration`, `source`. Duration 0 = lasts entire combat, positive = rounds remaining. `tick_effects()` decrements each round. `get_effect_bonus(effects, stat)` sums bonuses.
- **Stat modifiers**: `ac`, `attack_bonus`, `damage_bonus`, `damage_reduction` — applied in weapon attacks, ability attacks, and monster turns
- **Conditions** (same effect dict, special `stat`): `poison`/`burn`/`bleed` deal `value` damage at end of each round, `regen` heals, `stun` skips the bearer's turn. Bosses are immune to stun
- PP initialized on character creation, restored on rest, recalculated on level up

### Ability Scores

- Starting scores = race defaults + race bonus + class `ability_bonuses` (`json/classes_properties.json`: +4 primary, +2 secondary)
- **Ability Score Improvements**: 2 points at each of levels 4, 8, 12, 16, 19 (`ASI_LEVELS`), +1 per point, cap 20. Unspent points are derived (`asi_points_available()` = earned for level − spent), so old saves get theirs automatically
- Spent points live in `Character.ability_increases` (`{"strength": 2, ...}`), serialized with the character and re-applied by `apply_ability_increases()` in `_restore_character()` — characters are rebuilt from the factory on every request, so scores themselves are never stored
- `improve_ability()` handles side effects: Constitution adds `level` HP per modifier point, the class primary ability grows the PP pool, AC is recalculated
- AC is always derived (`update_ac()` on restore), never read from the save. `unarmored_defense` in class data (Monk: Wisdom, Barbarian: Constitution) adds that modifier to AC when no armor is worn
- UI: `/character/summary` is the character sheet with +1 buttons (`POST /character/improve`); the nav shows a badge while points are unspent

### Quest System

JSON-driven quest system with kill and gather quest types:
- **Data**: `json/quests.json` — 9 quests across 3 acts (4 Act 1, 3 Act 2, 2 Act 3)
- **Quest types**: Kill quests track monster kills; gather quests drop `QuestItem`s with a % chance on matching monster kills
- **Engine**: `engine/quests.py` — `check_quest_progress()` called after each kill, `turn_in_quest()` handles rewards and inventory cleanup
- **Session state**: `active_quests: dict` (`{quest_id: {"progress": int, "status": "active"|"ready"}}`), `completed_quests: list` (max 3 active)
- **Shop UI**: 3-tab interface (Wares/Sell/Quests) in `web/templates/shop/index.html`. Quest board shows available + active quests with progress bars, accept/turn-in/abandon actions
- **Routes**: `POST /shop/quest/accept`, `POST /shop/quest/turn-in`, `POST /shop/quest/abandon`
- **Rewards**: Gold + XP granted on turn-in; gather quest items removed from inventory on completion
- **Dialog**: Shopkeeper Elara has quest-specific dialog lines in `json/shopkeeper.json`

### Battle System

Combat is handled via `web/routes/battle.py` with game logic in `engine/`:

- **Round loop**: every player action ends in `finish_player_turn()` — monster turn (skipped if stunned) → end-of-round conditions (DoT/regen) → tick effects and cooldowns → next round. A stunned player loops again and loses their turn. Add new player actions by mutating state and returning `await finish_player_turn(request, session)`
- **Critical hits**: natural 20 always hits and doubles damage dice; natural 1 always misses (weapon attacks and attack-roll abilities, both sides)
- **Monster abilities**: `json/monster_abilities.json` (`races` → ability ids, `abilities` → definitions with `kind` attack/save/self, `cooldown`, `use_below_hp`, `lifesteal`, effects). Timed effects applied on the monster's turn get +1 duration because the monster acts last in the round
- **Bosses**: `json/bosses.json`, keyed by the `boss` id on a `campaign.json` area. Built with `CombatantState.from_boss()` (authored HP/AC/scores, no factory). Enrage once at ≤50% HP, cannot be fled, fixed XP/gold rewards, guaranteed loot. Started via `POST /battle/boss` or `begin_boss_battle()` (travel ambush)
- **Flee**: `POST /battle/flee` — d20 + DEX vs DC 10 + monster level // 2; failure costs the turn
- **Player defend** is a 1-round `ac` effect, not a mutation of `armor_class`
- **Monster state**: `CombatantState` dataclass (in `engine/combatant.py`) with `to_dict()`/`from_dict()`/`from_monster()` for serialization
- **Attack resolution**: `engine/combat.py` `resolve_weapon_attack()` — d20 + ability mod + proficiency + effect bonuses vs AC + effect bonuses. Returns `{hit, attack_roll, target_ac, damage}`
- **Weapon modifiers**: `get_weapon_attack_modifier()` — finesse uses max(STR,DEX), ammunition uses DEX, else STR
- **Monster AI**: `choose_monster_action()` — heal when wounded, use abilities off cooldown (chance rises with level; higher for bosses), otherwise attack/defend
- **Effects**: `engine/effects.py` — `tick_effects()` per round, `get_effect_bonus()` for stat queries
- **Battle actions**: `POST /battle/attack`, `POST /battle/defend`, `POST /battle/ability` (with `ability_id` form field), `POST /battle/item`, `POST /battle/flee`
- **Battle screen**: abilities are cards (`.ability-card`) with cost, description and stat lines; identical items share one button. Hotkeys via `data-hotkey`: A/D/F, 1–5 abilities, Q/W/E/R items
- **Hit feedback**: the page reloads after every action, so `initBattleFeedback()` keeps the previous HP in `sessionStorage` (keyed by `data-battle-key` + round) and shows floating damage numbers and an animated HP bar from the difference. Combatants carry `data-combatant`, `data-hp`, `data-max-hp`
- **Victory**: `battle_rewards` stays in the session until the next battle ends, so the victory page survives a refresh
- **Monster data**: Taunts in `json/monster_taunts.json`, portraits in `json/monster_portraits.json`
- **Player portraits**: Selected during character creation (3 options: Knight, Berserker, Wizard). Stored in `CharacterCreationState.portrait`

### Campaign Progression

- `GameSession.defeated_bosses` is the only stored progression state; unlocked act, shards and completion are **derived** by `engine/campaign.py`
- An act is complete when every boss placed on one of its areas is defeated → next act unlocks for travel (`/game/travel` lists all acts, locked ones greyed out)
- Bosses may declare `requires` (other bosses first — Malachar needs Lady Vex), `shard` (crown shard awarded), `ambush` (`{"act", "after_act_bosses"}` — sprung on travel; Lady Vex in Act 2)
- `GET /game/journal` shows main quest, shards, bosses, stats; `GET /game/ending` is the epilogue once all acts are complete

### Location Screen

- `build_area_map(location, current_area, defeated_bosses)` in `web/routes/game.py` lays the location's areas out top-down: row = steps from the location's first area, positions in percent. The template draws edges in an SVG and nodes as absolutely positioned boxes; only areas one step away are buttons (`POST /game/move`)
- Node markers: danger band on the top border (`_danger()`: safe/low/med/high from `encounters`), Shop, Rest, Boss/Cleared tags
- Hotkeys: E explore, R rest, S shop, T travel

### Exploration Events

- `POST /game/explore`: encounter roll first; otherwise `EVENT_CHANCE` (65%) to pick an event from `json/events.json`
- Events are filtered by `location_types`; events with `special` only fire in areas with that `special` string, take priority, and are `once`
- Each choice is a skill check (`skill`, `dc`, `success`/`failure` outcomes) or a no-check `outcome`. Outcome keys: `text`, `gold`, `xp`, `heal_pct`, `pp`, `damage` `[count, size]`, `potion`, `battle`. Rewards and DCs scale with the location tier (low end of `encounterLevel`)
- State: `pending_event` (awaiting choice — `/game` redirects to `/game/event`), `event_result` (shown once), `completed_events`
- Routes: `GET /game/event`, `POST /game/event/choose`, `POST /game/event/continue`

### Balance

Class kits, boss and monster numbers were tuned with `tools/balance_sim.py`, which plays fights through the real routes (`python tools/balance_sim.py bosses` / `monsters`, see its docstring; pass `--classes` with all 12 names for a class comparison). Targets: every class averages roughly 60–80% against at-level bosses with 3 potions (the simulated player spends its ASIs on the primary ability), regular fights 90%+ with most HP left. The simulator never uses one-round defensive abilities (Arcane Shield, Patient Defense, Cunning Dodge), so classes built around them are slightly better in real play than their numbers. Re-run it after changing combat numbers.

### Web Application (`web/`)

- **`web/app.py`** → FastAPI app, mounts static files, includes route blueprints at `/character`, `/game`, `/battle`, `/shop`, `/inventory`
- **`web/game_session.py`** → `GameSession` class with server-side file storage. Contains `CharacterCreationState`, `BattleState`, quest state, shop state, and references to campaign location/area data. Character objects are recreated from factory on each request via `_restore_character()`. Also contains JSON data loaders with caching.
- **`web/dependencies.py`** → FastAPI dependencies `require_character` and `require_battle` for route guards (replaces boilerplate `if not session.character` checks)
- **Inventory** (`web/routes/inventory.py`): `POST /inventory/use` drinks a healing potion outside battle; identical potions and quest items are stacked; backpack weapons show average damage and armor shows resulting AC (`Character.ac_if_wearing()`) against what is equipped
- **Character creation**: class cards show `playstyle` (from `classes_properties.json`) and the class's abilities; the details page previews final scores, HP, PP and the AC for each armor choice
- **Nav**: XP progress bar under the level (`xp_to_next_level` in the serialized character)
- **Routes** use server-side rendering with Jinja2 templates and POST/Redirect/GET pattern (303 redirects)
- **Templates** are rendered with `templates.TemplateResponse(request, "name.html", {...})` (request first — required by current Starlette)
- **Templates** in `web/templates/` extend `base.html` — all styling in `web/static/css/style.css`, all JS in `web/static/js/main.js` (no inline styles/scripts in templates)

### Session / Save System

Game state uses **server-side file storage**:
- **Cookie**: Contains only a `session_id` string (~100 bytes) via Starlette `SessionMiddleware`
- **Server files**: `web/sessions/{session_id}.json` stores the full serialized `GameSession`
- **`get_session(request)`**: Reads session_id from cookie, loads JSON file from disk
- **`save_session(request, session)`**: Writes JSON file to disk, sets session_id in cookie
- **Flash messages**: `session.set_flash(key, value)` / `session.pop_flash(key)` for one-time display messages (shop notifications, inventory messages)
- **All state in one place**: Character, battle, shop inventory, haggle state, quest progress, battle rewards — all stored in `GameSession.to_dict()`, no scattered `request.session` keys

### Shop System

- **Shopkeeper NPC** (Elara) with portrait and dialog system — all dialog lines in `json/shopkeeper.json`
- **Default inventory** in `json/shop_inventory.json`
- **Haggling**: Persuasion skill check → tiered discounts (nat20: 40% off, nat1: 25% markup). Each item can only be haggled once per restock
- **Buy/sell** with price calculation (sell = 50% of buy price)
- **Restocking**: After 10 monster kills or player death
- **3-tab UI**: Wares, Sell, Quests — tab state preserved via `?tab=` query param
- **Quest items filtered** from sell list (can't sell quest items)

### UI Design System (`web/static/css/style.css`)

Consolidated CSS design system with:
- CSS custom properties for colors, spacing, typography, radii, shadows
- Cinzel font for headings (loaded from Google Fonts in `base.html`)
- Reusable components: `.glass`, `.panel`, `.btn-*`, `.selection-card`, `.stat-box`, `.health-bar`, `.toast`, `.steps` (step indicator), `.effect-badge`, `.btn-ability`/`.btn-ability-free`
- Battle arena uses glassmorphism with background image overlay
- Portrait styles: `.player-portrait`, `.monster-portrait`, `.summary-portrait`, `.portrait-grid` (selection)
- Shop tabs: `.shop-tabs`, `.shop-tab`, `.shop-tab-panel`
- Quest board: `.quest-card`, `.quest-progress-bar`, `.quest-type-badge`
- Monster taunt bubble: `.monster-taunt`
- Bosses: `.boss-panel` (location), `.boss-banner`, `.combatant.boss`/`.enraged`, `.boss-defeat-panel`, `.shard-gem`
- Events: `.event-card`, `.event-choice`, `.outcome-chip`; reuses `.haggle-roll-result` for the d20 breakdown
- Journal/travel: `.journal-act`, `.shard-row`, `.travel-act`, `.loc-tag`
- Area map: `.area-map`, `.map-node`, `.map-edge`, `.map-tag`, `.map-danger-*`
- Battle feedback: `.ability-card`, `.float-number`, `.took-hit`/`.took-heal`; HP bar colour via `.hp-mid`/`.hp-low`
- `kbd` key hints (hidden on touch devices), `.xp-bar`, `.item-compare`, `.char-preview`, `.class-abilities`
- On phones the two combatants stay side by side
- Responsive breakpoints at 768px and 480px

### JavaScript (`web/static/js/main.js`)

- `SFX` object: Web Audio API synthesized sounds (hit, crit, miss, heal, defend, spell, victory, defeat, levelup, coin, click)
- Toast notification system (`showToast`, `initToasts` — reads `data-toast` elements)
- Confetti effect (`showConfetti`) and screen shake (`screenShake`) triggered by `data-confetti`/`data-screen-shake` attributes
- `initShopTabs()`: Tab switching with URL param auto-select (`?tab=quests`)
- `initHotkeys()`: pressing a key clicks the enabled element with that `data-hotkey`; ignored while typing in a field
- `initSubmitGuard()`: a POST form can only be submitted once per page load
- `initBattleFeedback()`, `initFillBars()` (`data-fill` bars animate on load), `initArmorPreview()`
- Selection card handler, skill counter, battle log auto-scroll, health bar coloring, active nav link detection

### Game World (`json/campaign.json`)

Campaign data defines acts → locations → areas. Each area has `connections` (list of area IDs for navigation), `encounters` (0-10 rating for encounter chance), `monster_types`, optional `special` strings (e.g., "shop", "inn" which enable shop/rest features in the web UI, or a key matched by one-time events), and optional `boss` (id into `json/bosses.json`).

### Key Design Patterns

- Factories load JSON config once and create domain objects
- Ability modifiers derived as `(score - 10) // 2` everywhere
- `sys.path.insert(0, ...)` used in web modules to import root-level game modules
- `CombatantState` dataclass stores monster battle state with `to_dict()`/`from_dict()` for serialization
- `BattleState` has backward-compatible properties proxying to `CombatantState` for gradual migration
- Shop restocks after 10 monster kills or player death
- All game data is JSON-driven — abilities, quests, taunts, portraits, shopkeeper dialog, shop inventory
- Active effects are flat stat modifiers (`{stat, value, duration, source}`) applied per-round via `get_effect_bonus()`
- Server-side session files replace cookie storage — no 4KB limit, state persists across browser restarts
- Flash messages (`set_flash`/`pop_flash`) for one-time notifications
- FastAPI `Depends()` for route guards (`require_character`, `require_battle`)
- `Character.level_up()` and `gain_xp()` return result dicts instead of printing — callers decide presentation
