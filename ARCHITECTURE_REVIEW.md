# Architecture Review & Recommendations

> Evaluation of AIVentures against modern game development and software engineering principles.
> Written 2026-03-17. Intended as a living document — update as changes land.

---

## Executive Summary

AIVentures is a well-functioning D&D 5e text RPG with a solid feature set. The JSON-driven data design and factory pattern are good foundations. However, the codebase has grown organically and now has several structural issues that will compound as features are added. The main concerns are: **duplicated game logic between layers**, **a monolithic session object that mixes every concern**, **tight coupling between routes and game rules**, and **no event system to coordinate cross-cutting features** (quests reacting to kills, shop restocking, etc.).

The recommendations below are ordered by impact and designed to be adopted incrementally — each one can be done as a standalone refactor alongside normal feature work.

---

## 1. Duplicated Game Logic (Critical)

**Problem:** Battle resolution, level-up, damage calculation, and monster creation are reimplemented in the web routes rather than reusing the domain model. The CLI (`battleAI.py`, `character.py`) and web (`web/routes/battle.py`) have diverged into two separate games sharing only the entity classes.

Examples:
- `Character.level_up()` (character.py:118) uses `input()` for HP rolls — unusable from the web. So `end_battle()` (battle.py:825-833) reimplements leveling inline.
- `Character.level_up()` calls `input()` — a blocking CLI call baked into a domain object.
- `Entity.take_damage()` uses `damage_reduction` from the entity, but `battle.py` applies `get_effect_bonus(..., "damage_reduction")` separately and never calls `take_damage()`.
- `Entity.equip()`/`unequip()` print to stdout — side effects in domain logic.
- `calculate_sell_price()` in shop.py recalculates item value from scratch rather than items having a known value.

**Impact:** Every new combat feature (status effects, boss mechanics, monster abilities) must be implemented twice, or the CLI falls further behind. Bugs fixed in one place won't be fixed in the other.

**Recommendation: Extract a headless game engine**

Create a `game/` package (or `engine/`) with pure-logic functions that both the CLI and web can call:

```
engine/
  combat.py      — resolve_attack(), resolve_ability(), monster_turn(), end_combat()
  leveling.py    — apply_xp(), level_up() (no input(), returns results)
  effects.py     — tick_effects(), get_effect_bonus(), apply_effect()
  loot.py        — (move LootGenerator here)
  quests.py      — check_quest_progress(), turn_in_quest()
```

The web routes become thin: parse request -> call engine -> save session -> redirect. The domain objects (`Entity`, `Character`, `Monster`) become pure data holders with no I/O.

**When to do this:** Before adding any new combat features (monster abilities, boss fights). Each new feature will otherwise deepen the duplication.

---

## 2. God Object: GameSession (High)

**Problem:** `GameSession` is a 590-line class that owns character state, battle state, shop state, quest state, flash messages, creation wizard state, location state, and serialization logic. It's the single point of coupling for every feature.

Consequences:
- Adding any feature means modifying `GameSession.to_dict()`, `from_dict()`, and `_serialize_character()`.
- `_restore_character()` is 90 lines of fragile reconstruction logic that re-creates a `Character` from scratch every request, including re-equipping items, re-applying skills, and parsing potion names with string matching (lines 538-550).
- Every route file imports the same `get_session`/`save_session` pair and directly mutates session fields — no encapsulation.

**Recommendation: Split GameSession into composed sub-states**

```python
@dataclass
class GameSession:
    session_id: str
    character_state: CharacterState      # name, race, class, stats, inventory, equipment
    battle_state: BattleState            # already exists, just needs its own serialize/deserialize
    world_state: WorldState              # act, location, area
    quest_state: QuestState              # active_quests, completed_quests
    shop_state: ShopState                # inventory, haggled_items
    flash: FlashMessages                 # _flash dict
```

Each sub-state owns its own `to_dict()` / `from_dict()`. This means adding quest features only touches `QuestState`, not the whole session.

**When to do this:** Can be done incrementally. Start by extracting `BattleState` serialization (it's already a dataclass). Then `ShopState`. Then tackle `CharacterState` — the hardest part, because of `_restore_character()`.

---

## 3. No Event System (High)

**Problem:** Cross-cutting game events (monster killed, item acquired, level gained, area entered) are handled with inline checks scattered across routes. For example, `end_battle()` in battle.py (lines 862-889) manually loops through active quests to check kill/gather progress. Shop restocking is checked after every kill (line 849). Level-up triggers PP recalculation inline (line 838).

This means every new feature that reacts to game events (achievements, story triggers, NPC reactions, boss unlocks, area-gated content) requires editing `end_battle()` or `explore()` — making those functions grow unboundedly.

**Recommendation: Introduce a simple event bus**

```python
# engine/events.py
class GameEvent:
    pass

@dataclass
class MonsterKilled(GameEvent):
    monster_race: str
    monster_level: int
    area_id: str

@dataclass
class LevelGained(GameEvent):
    new_level: int
    class_name: str

# Simple pub/sub — no async needed for a turn-based game
class EventBus:
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def on(self, event_type, handler):
        self._handlers[event_type].append(handler)

    def emit(self, event):
        for handler in self._handlers[type(event)]:
            handler(event)
```

Then quest progress, shop restocking, achievement checks, and story triggers are just handlers registered against `MonsterKilled`. Adding a new system means adding a handler, not editing battle code.

**When to do this:** Before adding achievements, story events, boss triggers, or any other reactive system. Pair it with the engine extraction (#1) — events are emitted from engine functions.

---

## 4. Monster as Flat Fields Instead of Object (Medium)

**Problem:** `BattleState` stores the monster as 15+ individual fields (`monster_name`, `monster_hp`, `monster_ac`, `monster_str_modifier`, ...) rather than a composed object. This was done for "serialization" but it means:

- `start_battle()` (battle.py:334-348) manually copies every field from the `Monster` object to `BattleState`.
- `execute_monster_turn()` reads `battle.monster_str_modifier`, `battle.monster_weapon_damage_die`, etc. — it's talking to a flattened dict, not an object with behavior.
- Adding a field to monsters (e.g., `monster_abilities`, `monster_resistances`) means adding it to `BattleState`, `to_dict()`, `from_dict()`, and `start_battle()`.

**Recommendation:** Create a serializable `CombatantState` dataclass used for both player and monster in battle:

```python
@dataclass
class CombatantState:
    name: str
    race: str
    level: int
    hp: int
    max_hp: int
    ac: int
    base_ac: int
    str_mod: int
    dex_mod: int
    proficiency: int
    weapon: WeaponState  # sub-dataclass
    effects: list[EffectState]

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data) -> "CombatantState": ...

    @classmethod
    def from_monster(cls, monster: Monster) -> "CombatantState": ...
```

This eliminates the field-by-field copying and makes it trivial to add monster abilities later — just add fields to `CombatantState`.

**When to do this:** Before adding monster abilities or boss mechanics.

---

## 5. Character Reconstruction on Every Request (Medium)

**Problem:** `_restore_character()` (game_session.py:463-555) creates a fresh `Character` via `CharacterFactory` on every single HTTP request, then manually patches 20+ fields back onto it. This is fragile — it parses potion names via string matching ("Minor" → 5, "Greater" → 20), silently swallows errors (`except ValueError: pass`), and re-instantiates `WeaponFactory` and `ArmorFactory` each time.

**Recommendation:** Characters should serialize/deserialize themselves. Add `Character.to_dict()` and `Character.from_dict()` methods that handle their own state without needing factories. Store the full character state in the session JSON, not just creation params.

```python
class Character(Entity):
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "race": self.race,
            # ... all fields
            "inventory": [item.to_dict() for item in self.inventory],
            "weapon_slots": {slot.name: w.to_dict() if w else None for slot, w in self.weapon_slots.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character": ...
```

This also means `Item`, `Weapon`, `Armor`, `HealingPotion`, and `QuestItem` each need `to_dict()` / `from_dict()`. This is a larger refactor but eliminates the most fragile code in the project.

**When to do this:** When you're ready to tackle save/load or when the current reconstruction breaks (e.g., adding new item types).

---

## 6. sys.path Manipulation (Medium)

**Problem:** Every web module starts with `sys.path.insert(0, ...)` to import root-level game modules. This is brittle, creates implicit dependencies, and breaks IDE tooling.

```python
# Found at the top of every web/ file:
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
```

**Recommendation:** Convert to a proper Python package with a `pyproject.toml` or at minimum an installable structure:

```
aiventures/
  __init__.py
  domain/         # entity.py, character.py, monster.py, weapon.py, etc.
  engine/         # combat.py, leveling.py, effects.py, etc.
  data/           # json/ files
  web/            # FastAPI app
  cli/            # main.py
```

Install with `pip install -e .` and use normal imports everywhere. This is a larger refactor but pays for itself in tooling support and eliminates a class of import-order bugs.

**When to do this:** During a dedicated cleanup sprint, or when you add the `engine/` package (#1).

---

## 7. Route Functions Contain Business Logic (Medium)

**Problem:** Route handlers do too much. `player_attack()` (battle.py:471-538) calculates attack rolls, applies damage, checks effects, executes monster turns, ticks effects, and advances rounds — all in one 70-line function. `shop_view()` (shop.py:160-272) builds quest state, calculates prices, assembles template context — 110 lines.

This makes routes hard to test (you need HTTP requests to test game logic) and hard to reuse (the CLI can't call these).

**Recommendation:** Routes should be 5-15 lines: parse input, call engine, format response.

```python
@router.post("/attack")
async def player_attack(request: Request):
    session = get_session(request)
    if not session.battle.is_active:
        return RedirectResponse("/battle", status_code=303)

    result = engine.combat.player_attack(session)  # all logic here

    if result.battle_ended:
        save_session(request, session)
        return RedirectResponse(f"/battle/{result.outcome}", status_code=303)

    save_session(request, session)
    return RedirectResponse("/battle", status_code=303)
```

**When to do this:** Part of the engine extraction (#1).

---

## 8. Static Data in Python Files (Low-Medium)

**Problem:** Monster taunts (250 lines), monster portraits (dict), shopkeeper dialog (106 lines), and default shop inventory are hardcoded in Python route files. This is inconsistent with the otherwise JSON-driven data design.

**Recommendation:** Move to JSON data files alongside the other game data:

```
json/
  monster_taunts.json
  monster_portraits.json
  shopkeeper.json
  shop_inventory.json
```

Load them through the same caching pattern used for `abilities.json`, `quests.json`, etc. This keeps all content in one place and makes it easy for non-programmers to edit game content.

**When to do this:** Whenever you're editing monster taunts or shop dialog. Low risk, easy to do piecemeal.

---

## 9. No Input Validation Layer (Low-Medium)

**Problem:** Route handlers do their own validation inline with `if not session.character: return RedirectResponse(...)`. This pattern is repeated at the top of every single route (~20 times). Battle routes also check `if not session.battle.is_active`.

**Recommendation:** Use FastAPI dependencies for common guards:

```python
async def require_character(request: Request) -> GameSession:
    session = get_session(request)
    if not session.character:
        raise HTTPException(status_code=303, headers={"Location": "/character/new"})
    return session

async def require_battle(session: GameSession = Depends(require_character)) -> GameSession:
    if not session.battle.is_active:
        raise HTTPException(status_code=303, headers={"Location": "/game"})
    return session

@router.post("/attack")
async def player_attack(session: GameSession = Depends(require_battle)):
    # no boilerplate needed
```

**When to do this:** Anytime. Low risk, reduces boilerplate.

---

## 10. Side Effects in Domain Objects (Low-Medium)

**Problem:** `Entity.equip()`, `Entity.unequip()`, `Character.equip_weapon()`, `Character.level_up()` all call `print()`. `Character.level_up()` calls `input()`. Domain objects should be pure data + logic with no I/O.

**Recommendation:** Remove all `print()` and `input()` from domain classes. Return result objects instead:

```python
def level_up(self, roll_hp=False) -> LevelUpResult:
    self.level += 1
    # ...
    return LevelUpResult(new_level=self.level, hp_gained=hp_increase)
```

Let the caller (CLI or web) decide how to present results.

**When to do this:** Part of the engine extraction (#1), or as a standalone cleanup.

---

## 11. Test Coverage Gaps (Low)

**Problem:** The test suite (39 tests) covers core mechanics but has no tests for:
- Web routes (no HTTP-level tests)
- Session serialization/deserialization roundtrips
- Quest progress tracking
- Shop buy/sell/haggle
- Level-up HP calculations
- Effect stacking and duration

**Recommendation:** Add integration tests for the web layer using FastAPI's `TestClient`. Prioritize testing session roundtrips (serialize → deserialize → verify all state preserved) since that's where the most fragile code lives.

**When to do this:** Before any serialization refactors (#2, #5) to catch regressions. Add tests for each new feature as it's built.

---

## 12. Global Mutable Caches (Low)

**Problem:** JSON data is cached in module-level globals (`_races_cache`, `_classes_cache`, etc.) with manual "load once" patterns. This works but isn't thread-safe and makes testing harder (can't inject test data).

**Recommendation:** Use `@functools.lru_cache` or a simple registry class:

```python
@lru_cache(maxsize=1)
def get_races() -> dict:
    return load_json("races.json")
```

Or for testability, a data registry that can be reset:

```python
class DataRegistry:
    def __init__(self, json_dir: Path):
        self.json_dir = json_dir
        self._cache = {}

    def get(self, filename: str) -> dict:
        if filename not in self._cache:
            self._cache[filename] = load_json(self.json_dir / filename)
        return self._cache[filename]
```

**When to do this:** During the package restructure (#6), or when you need to write tests that use different data.

---

## Priority Roadmap

Recommended order for tackling these alongside feature development:

| Phase | Refactor | Pairs well with feature |
|-------|----------|------------------------|
| **Now** | #10 Remove print/input from domain | Any feature work |
| **Now** | #8 Move taunts/dialog to JSON | Adding new monsters or NPCs |
| **Next** | #1 Extract game engine | Monster abilities, boss fights |
| **Next** | #3 Event system | Achievements, story triggers |
| **Next** | #4 CombatantState dataclass | Monster abilities |
| **Soon** | #2 Split GameSession | Save/load, new state systems |
| **Soon** | #7 Thin routes | Any new routes |
| **Soon** | #9 FastAPI dependencies | Any new routes |
| **Later** | #5 Character self-serialization | Save/load system |
| **Later** | #6 Package restructure | When imports get painful |
| **Later** | #11 Test coverage | Before any major refactor |
| **Later** | #12 Cache cleanup | During package restructure |

---

## What's Already Good

Credit where due — these patterns should be preserved:

- **JSON-driven data design**: Abilities, quests, weapons, armor, races, classes, campaign are all data files. This is excellent and should be extended (taunts, portraits, shop inventory).
- **Factory pattern**: Clean separation between data definition and object creation.
- **Server-side sessions**: The file-based session system with cookie-only IDs is simple and effective. No 4KB cookie limits, survives browser restarts.
- **POST/Redirect/GET**: Correct HTTP pattern throughout. No double-submit issues.
- **Flash messages**: Clean one-time notification system.
- **Effect system**: The flat `{stat, value, duration, source}` model is simple, composable, and easy to extend.
- **Dataclass for BattleState**: Good use of dataclasses for structured state (just needs to go further).
- **CSS design system**: Custom properties, component classes, responsive breakpoints — well organized.
- **Web Audio SFX**: Synthesized sounds with no audio file dependencies — clever and lightweight.
