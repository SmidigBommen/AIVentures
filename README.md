# AIVentures — The Shattered Crown

A D&D 5e-inspired text adventure game built in Python with a modern web UI.

## About

AIVentures is a single-player RPG set in the realm of Eldoria, where the dark sorcerer Malachar is gathering fragments of the Shattered Crown. Players create a character, explore a 3-act campaign world, battle monsters, collect loot, complete quests, and level up — all driven by D&D 5e-style mechanics.

Started as an experiment using AI as a co-coder, it has grown into a full-featured game with a FastAPI + Jinja2 web interface featuring a polished dark fantasy theme.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn web.app:app --reload --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 in your browser.

## Features

### Character System
- 12 races with unique ability score bonuses
- 11 classes: Fighter, Wizard, Rogue, Cleric, Barbarian, Paladin, Ranger, Monk, Bard, Sorcerer, Warlock, Druid
- 6 ability scores (STR/DEX/CON/INT/WIS/CHA) with D&D 5e modifier calculation
- Skill proficiency selection based on class
- Equipment system with weapon and armor slots, proficiency checks
- XP-based leveling with HP increases
- Player portrait selection during character creation (Knight, Berserker, Wizard)

### Magic & Ability System
- **Power Points (PP)**: Universal resource pool — full casters get more, martial classes get fewer but impactful abilities
- **55 unique abilities** across all 11 classes (5 per class), defined in `json/abilities.json`
- Each class has a free cantrip/basic ability (0 PP) plus 4 costed abilities (1-3 PP) unlocking at levels 1, 2, 4, and 6
- Ability types: damage (melee/spell attack, spell save, auto-hit), healing, buffs (self), debuffs (enemy)
- Cantrips scale with level (more dice at levels 5, 11)
- Active effects modify attack rolls, damage, AC, and damage reduction
- Effects tick down each round; duration 0 = lasts entire combat
- PP recovers on rest
- New abilities shown on level-up victory screen

### Combat
- Turn-based battle system with D&D 5e mechanics
- d20 attack rolls + ability modifier + proficiency vs AC
- Initiative system (d20 + DEX modifier)
- Actions: Attack, Defend, Abilities, Items
- Monster AI: 70% attack, 30% defend
- Active buff/debuff effects from abilities apply to both sides
- Tier-based loot drops (potions, gold, weapons, armor)
- Victory rewards: XP, gold, loot, quest progress, level-up notifications
- Monster portraits and taunts — each of the 12 monster races has unique start, attack, and hurt dialog lines
- Player portraits displayed on the battle arena

### Quest System
- Shopkeeper Elara offers kill quests and gather quests
- **Kill quests**: Track monster kills of a specific type (e.g., "Kill 5 Goblins")
- **Gather quests**: Quest items drop with a % chance from specific monsters, stored in inventory
- 9 quests across 3 acts, scaling in difficulty and rewards
- Max 3 active quests at a time
- Quest progress shown on victory screen after each battle
- Quest board in the shop with accept, turn-in, and abandon actions
- Rewards: gold + XP on turn-in

### Shop & NPC
- Shopkeeper NPC (Elara) with portrait, dialog system, and context-sensitive lines
- Buy potions, sell equipment
- **Haggling system**: Roll a Persuasion check for discounts (nat 20 = 40% off, nat 1 = price goes up)
- 3-tab interface: Wares, Sell, Quests
- Shop restocks after 10 monster kills or player death

### World
- 3-act campaign ("The Shattered Crown") with 8 locations and 50+ interconnected areas
- Area-based navigation with encounter chance ratings
- 12 monster races with unique stats, weapons, and personalities
- Rest at inns/taverns to recover HP and PP
- Location travel between zones within each act

### Web UI
- Dark fantasy theme with Cinzel heading font
- Glassmorphism battle arena with background art
- Player and monster portraits in battle
- Monster taunt speech bubbles and combat dialog
- Animated health and PP bars
- Toast notification system
- Confetti on victory, screen shake on defeat
- Synthesized sound effects via Web Audio API (hit, miss, heal, spell, victory, defeat, level-up, coin)
- Step indicator for character creation flow
- Responsive design for mobile
- Active effect badges on combatants during battle

## Running Tests

```bash
pytest                          # all tests (148 tests)
pytest test/test_battle.py      # battle mechanics
pytest test/test_session_roundtrip.py  # session serialization
pytest test/test_engine_combat.py      # engine combat logic
```

## Tech Stack

- **Backend**: Python, FastAPI, uvicorn, Jinja2
- **Frontend**: Pure HTML/CSS/JS (no frameworks), Google Fonts (Cinzel)
- **Session**: Server-side JSON files (`web/sessions/`), cookie holds only session ID
- **Data**: JSON configuration files for races, classes, weapons, armor, monsters, abilities, quests, campaign

## Project Structure

```
AIVentures/
├── character.py               # Character class (player)
├── entity.py                  # Base Entity class (shared stats/mechanics)
├── monster.py                 # Monster class (enemies)
├── items.py                   # Item, HealingPotion, QuestItem classes
├── *Factory.py                # Factory classes for creating game objects
├── engine/                    # Headless game logic (no I/O, no web deps)
│   ├── combat.py              # Attack resolution, rewards
│   ├── effects.py             # Buff/debuff duration and stacking
│   ├── leveling.py            # PP calculation
│   ├── quests.py              # Quest progress and turn-in
│   └── combatant.py           # CombatantState dataclass for battle
├── json/                      # Game data files
│   ├── campaign.json          # World: acts, locations, areas
│   ├── abilities.json         # 55 class abilities
│   ├── quests.json            # 9 quests across 3 acts
│   ├── weapon-catalog.json    # Weapon definitions
│   ├── armor_catalog.json     # Armor definitions
│   ├── classes_properties.json # Class stats, proficiencies
│   ├── races.json             # Race ability bonuses
│   ├── monster_default_values.json # Monster race stats
│   ├── monster_taunts.json    # Monster dialog lines
│   ├── monster_portraits.json # Monster portrait mappings
│   ├── shopkeeper.json        # Shopkeeper NPC dialog
│   └── shop_inventory.json    # Default shop items
├── web/
│   ├── app.py                 # FastAPI application
│   ├── game_session.py        # Session management, data loaders
│   ├── dependencies.py        # FastAPI route guards
│   ├── sessions/              # Server-side session JSON files
│   ├── routes/
│   │   ├── character.py       # Character creation flow
│   │   ├── game.py            # World navigation, exploration, rest
│   │   ├── battle.py          # Combat system
│   │   ├── shop.py            # Shop, haggling, quests
│   │   └── inventory.py       # Equipment management
│   ├── templates/             # Jinja2 HTML templates
│   └── static/
│       ├── css/style.css      # Complete design system
│       ├── js/main.js         # Sound effects, toasts, tabs, animations
│       └── images/            # Portraits (player, monster, shopkeeper)
└── test/                      # pytest test suite (148 tests)
```

## Worklist

Status | Feature
-------|--------
Done | Core combat system (attack rolls, AC, damage, initiative)
Done | Character creation with race/class/portrait selection
Done | Equipment system (weapons, armor, inventory management)
Done | XP and leveling system
Done | Campaign world with locations and areas
Done | Shop with buy/sell, haggling, and restocking
Done | Web UI with FastAPI + Jinja2
Done | UI/UX redesign (glassmorphism, animations, sound effects, responsive design)
Done | Magic/ability system (Power Points, 55 abilities across 11 classes)
Done | Active effects (buffs/debuffs) in combat
Done | NPC shopkeeper with dialog system
Done | Quest system (kill & gather quests, quest board, rewards)
Done | Monster portraits and taunts
Done | Player portraits (selection at character creation)
Done | Server-side session storage (JSON files, no cookie size limits)
Done | Game engine extraction (engine/ package — combat, effects, quests, leveling)
Done | CLI removal — web-only codebase
x | Boss encounters with unique mechanics
x | Act progression gating
x | Monster abilities and smarter AI
x | Spells/abilities for exploration (outside combat)
x | Off-hand / dual wielding
