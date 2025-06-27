# AIVentures

Just playing around with some Python code and ChatGPT/Claude as co-coder to test out limits and benefits it could possibly have for developers and testers

Initial Scope:
Create characters and monsters
roll dice
engage in battle based in dice rolls
add items and more attributes

## Worklist items ##
_This is an iterative approach so done only means an iteration is done and an initial implementation is in place_

Status | Ideas / Feature
-------| ------
Done | Dice roll
Done | Monster creation
Done | Initiative (Who goes first)
Done | Combat (1 character vs 1 monster)
Done | Armor (minus vs an attack roll)
Done | Turns
Done | Level up (xp + add more stats?)
Done | Armor Class (AC) - Does the hit actually land (hit calculation)
Done | Initial Hit points on player calculated based on class (con + class modifier)
Done | Weapons (adds to an damage roll)
Done | Added choice to roll or take average on HP increase at level up.
Done | Refactor weapons to be a specific variable and not a general item
Done | Monster initial hit points based on level and dice rolls at creation including CON modifier
Fixed | Bug: Monster attack rolls (defence choice is not cleared) are not being calculated correctly
Fixed | Bug: Barbarian does not get correct skills. This can be becasue the class is a DEX class in the setup, book says strength..
Done | Locations: add more locations and implement the transitions between them
Done | Locations: Areas in each locations is implemented with connection to eachother
Fixed| Bug: transition out of area after combat does not seem to work correctly when you have changed location
 x | Special: Some areas have special attribute with some hidden element. Implement interaction these specials with skill rolls
 x | Improvement: Add starting equipment according to class (D&D 5e Player Handbook 2024 : Example of Core Fighter Traits, page 91)
 x | Improvement: Battle (end_battle) should maybe not handle the XP logic.
 x | Monsters have XP connected to them directly
 x | Group (More than one monster)
 x | Character Abilities: Design unique abilities for each character class, such as special attacks or spells. _Implement methods to use these abilities in battles and manage their resource costs (e.g., mana or energy)_
 x | Status Effects: Add conditions that can affect characters during battles, such as poison, paralysis, or buffs/debuffs. _Implement methods to apply, remove, and manage these effects_
 x | Equipment: Introduce equipment items that can be worn by characters to enhance their abilities, such as armor, weapons, or accessories. _Implement methods to manage equipment inventory and equip/un-equip items_
 x | Advanced Combat System: Develop a more strategic combat system, which can involve implementing a turn-based or real-time system, positioning, or unique tactics for each character class or enemy type.
 Done | Ability Scores: Add Ability Scores and Modifiers correctly on a character and monster.
 x | Ability Scores: Characters can decide to use a standard array and divide it onto different scores. Characters can decide to roll 4x6 dice an discard.  Two options.
 Done | Random Monster Encounter: Player doesnt meet same monster each time. (name and level changes)

### Implementing Additional Game Mechanics ###
* Armor Class (AC) - Does the hit actually land
* Different armor types (light/medium/heavy)
* Equipment slots
* Durability

### Future expansions ###
* Add Textual for the textGUI
* Add more monsters types