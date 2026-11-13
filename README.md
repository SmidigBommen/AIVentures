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
- Class training: every class starts with +4 to its primary ability and +2 to a second one
- **Ability Score Improvements** at levels 4, 8, 12, 16 and 19: two points to spend on the character sheet (max 20 per score). Constitution grants its HP retroactively
- Unarmored Defense for Monk (Wisdom) and Barbarian (Constitution)
- Skill proficiency selection based on class
- Equipment system with weapon and armor slots, proficiency checks
- XP-based leveling with HP increases
- Player portrait selection during character creation (Knight, Berserker, Wizard)

### Magic & Ability System
- **Power Points (PP)**: Universal resource pool — full casters get more, martial classes get fewer but impactful abilities
- **55 unique abilities** across all 11 classes (5 per class), defined in `json/abilities.json`
- Each class has a free cantrip/basic ability (0 PP) plus 4 costed abilities (1-3 PP) unlocking at levels 1, 2, 4, and 6
- Ability types: damage (melee/spell attack, spell save, auto-hit), healing, buffs (self), debuffs (enemy)
- Conditions: some abilities leave the target Poisoned, Burning or Bleeding (damage every round) or Stunned (lose a turn)
- Free abilities scale with level (more dice at levels 5 and 11); costed damage abilities and heals grow too, so spending PP stays worthwhile
- Monks draw on a larger ki-sized PP pool; Reckless Attack hits hard but lowers the Barbarian's own AC
- Active effects modify attack rolls, damage, AC, and damage reduction
- Effects tick down each round; duration 0 = lasts entire combat
- PP recovers on rest
- New abilities shown on level-up victory screen

### Combat
- Turn-based battle system with D&D 5e mechanics
- d20 attack rolls + ability modifier + proficiency vs AC
- Initiative system (d20 + DEX modifier)
- **Critical hits**: a natural 20 always hits and doubles the damage dice; a natural 1 always misses
- Actions: Attack, Defend, Abilities, Items, Flee (DEX check vs DC 10 + half the monster's level)
- **Monster abilities**: every monster race has its own special moves (Fire Breath, Life Drain, Regenerate, Howling Gale...) with cooldowns, saving throws and conditions — defined in `json/monster_abilities.json`
- **Monster AI**: uses abilities when off cooldown, heals when wounded, turtles when nearly dead, presses the attack when you are
- Active buff/debuff effects and conditions apply to both sides
- Tier-based loot drops (potions, gold, weapons, armor)
- Victory rewards: XP, gold, loot, quest progress, level-up notifications
- Monster portraits and taunts — each of the 12 monster races has unique start, attack, and hurt dialog lines
- Player portraits displayed on the battle arena

### Bosses & Campaign Progression
- **9 hand-authored bosses** (`json/bosses.json`) guard the boss areas of the campaign, each with unique abilities, an intro, taunts and a defeat scene
- Bosses **enrage at half health**, cannot be fled from, and shrug off stuns
- Five of them hold the **shards of the Crown of Unity** — collect all five
- **Act gating**: defeating every boss in an act unlocks travel to the next one
- **Lady Vex** ambushes you on the road once you hold two of Act 2's shards; her seal bars Malachar's door until you beat her again in Act 3
- Defeat Malachar to restore the Crown and see the **epilogue**
- **Journal** page tracks the main quest, shards, bosses and your deeds

### Exploration Events
- Exploring can now turn up **skill-check events** instead of only fights or nothing: locked chests, wounded travelers, shrines, traps, spirits...
- 23 events in `json/events.json`, each with several approaches using different skills (your modifier and the DC are shown before you choose)
- Natural 20s always succeed, natural 1s always fail; outcomes grant gold, XP, healing, power points, potions — or cost HP, gold, or start a fight
- **One-time discoveries** tied to special areas (the bridge runes, the dwarven forge, Malachar's laboratory...)

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
- Location travel between zones in every act you have unlocked

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
pip install pytest httpx         # httpx is only needed for the route tests
pytest                          # all tests (286 tests)
pytest test/test_battle.py      # battle mechanics
pytest test/test_session_roundtrip.py  # session serialization
pytest test/test_engine_combat.py      # engine combat logic
pytest test/test_web_flow.py           # end-to-end flows through the routes
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
│   ├── combat.py              # Attack resolution, crits, flee, rewards
│   ├── abilities.py           # Player class ability resolution
│   ├── monster_ai.py          # Monster action choice and special abilities
│   ├── effects.py             # Buff/debuff duration, stacking, conditions
│   ├── campaign.py            # Boss, shard and act progression rules
│   ├── events.py              # Exploration skill-check events
│   ├── leveling.py            # PP calculation
│   ├── quests.py              # Quest progress and turn-in
│   └── combatant.py           # CombatantState dataclass for battle
├── json/                      # Game data files
│   ├── campaign.json          # World: acts, locations, areas
│   ├── abilities.json         # 55 class abilities
│   ├── quests.json            # 9 quests across 3 acts
│   ├── bosses.json            # 9 bosses: stats, abilities, story text
│   ├── monster_abilities.json # Monster and boss special abilities
│   ├── events.json            # Exploration events
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
│   │   ├── game.py            # World navigation, exploration, events, travel, journal
│   │   ├── battle.py          # Combat system
│   │   ├── shop.py            # Shop, haggling, quests
│   │   └── inventory.py       # Equipment management
│   ├── templates/             # Jinja2 HTML templates
│   └── static/
│       ├── css/style.css      # Complete design system
│       ├── js/main.js         # Sound effects, toasts, tabs, animations
│       └── images/            # Portraits (player, monster, shopkeeper)
├── tools/
│   └── balance_sim.py         # Simulates boss/monster fights to check balance
└── test/                      # pytest test suite (286 tests)
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
Done | Boss encounters with unique mechanics (enrage, abilities, no fleeing)
Done | Act progression gating, crown shards, journal and ending
Done | Monster abilities and smarter AI
Done | Critical hits, conditions (poison/burn/bleed/stun) and fleeing
Done | Exploration events driven by skill checks
Done | Class balance pass (all 12 classes within the same win-rate band against bosses)
Done | Class ability bonuses and ability score improvements on level-up
x | Boss and remaining monster portraits
x | Spells/abilities for exploration (outside combat)
x | Off-hand / dual wielding
