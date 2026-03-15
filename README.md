# AIVentures — The Shattered Crown

A D&D 5e-inspired text adventure game built in Python with a modern web UI.

## About

AIVentures is a single-player RPG set in the realm of Eldoria, where the dark sorcerer Malachar is gathering fragments of the Shattered Crown. Players create a character, explore a 3-act campaign world, battle monsters, collect loot, and level up — all driven by D&D 5e-style mechanics.

Started as an experiment using AI as a co-coder, it has grown into a full-featured game with two interfaces:

- **Web UI** (active focus): FastAPI + Jinja2 server-rendered HTML with a polished dark fantasy theme
- **CLI** (legacy): Terminal-based game with ANSI colors

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
- Victory rewards: XP, gold, loot, level-up notifications with HP/PP/new ability display

### World
- 3-act campaign ("The Shattered Crown") with 8 locations and 50+ interconnected areas
- Area-based navigation with encounter chance ratings
- Rest at inns/taverns to recover HP and PP
- Shop system with buy/sell mechanics, restocks after 10 kills or death
- Location travel between zones within each act

### Web UI
- Dark fantasy theme with Cinzel heading font
- Glassmorphism battle arena with background art
- Animated health and PP bars
- Toast notification system
- Confetti on victory, screen shake on defeat
- Synthesized sound effects via Web Audio API (hit, miss, heal, spell, victory, defeat, level-up, coin)
- Step indicator for character creation flow
- Responsive design for mobile
- Active effect badges on combatants during battle

## Running Tests

```bash
pytest                          # all tests (39 tests)
pytest test/test_abilities.py   # ability system tests
pytest test/test_battle.py      # battle mechanics
pytest test/test_armor.py       # armor AC calculations
```

## Tech Stack

- **Backend**: Python, FastAPI, uvicorn, Jinja2
- **Frontend**: Pure HTML/CSS/JS (no frameworks), Google Fonts (Cinzel)
- **Session**: Starlette SessionMiddleware (signed cookies)
- **Data**: JSON configuration files for races, classes, weapons, armor, monsters, abilities, campaign

## Worklist

Status | Feature
-------|--------
Done | Core combat system (attack rolls, AC, damage, initiative)
Done | Character creation with race/class selection
Done | Equipment system (weapons, armor, inventory management)
Done | XP and leveling system
Done | Campaign world with locations and areas
Done | Shop with buy/sell and restocking
Done | Web UI with FastAPI + Jinja2
Done | UI/UX redesign (glassmorphism, animations, sound effects, responsive design)
Done | Magic/ability system (Power Points, 55 abilities across 11 classes)
Done | Active effects (buffs/debuffs) in combat
x | Boss encounters with unique mechanics
x | Quest system and act progression gating
x | NPC dialogue
x | Monster abilities and smarter AI
x | Spells/abilities for exploration (outside combat)
x | Off-hand / dual wielding
x | Save/load (server-side storage)
