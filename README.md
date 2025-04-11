# AIVentures

Just playing around with some Python code and ChatGPT/Claude as co-coder to test out limits and benefits it could possibly have for developers and testers

Initial Scope:
Create characters and monsters
roll dice
engage in battle based in dice rolls
add items and more attributes

## Worklist items ##
_This is an iterative approach so done only means an iteration is done and an initial implementation is in place_


Status | Ideas
-------| ------
Done | Dice roll
Done | Monster creation
Done | Initiative (Who goes first)
Done | Combat (1 character vs 1 monster)
Done | Armor (minus vs an attack roll)
Done | Turns
Done | Level up (xp + add more stats?)
Done | Armor Class (AC) - Does the hit actually land (hit calculation)
Done | Initial Hit points calculated based on class (con + class modifier)
In Progress | Weapons (adds to an attack roll)
 x | Group (More than one monster)
 x | Character Abilities: Design unique abilities for each character class, such as special attacks or spells. _Implement methods to use these abilities in battles and manage their resource costs (e.g., mana or energy)_
 x | Status Effects: Add conditions that can affect characters during battles, such as poison, paralysis, or buffs/debuffs. _Implement methods to apply, remove, and manage these effects_
 x | Equipment: Introduce equipment items that can be worn by characters to enhance their abilities, such as armor, weapons, or accessories. _Implement methods to manage equipment inventory and equip/un-equip items_
 x | Advanced Combat System: Develop a more strategic combat system, which can involve implementing a turn-based or real-time system, positioning, or unique tactics for each character class or enemy type.
 x | Ability Scores: Add Ability Scores and Modifiers correctly on a character.
 x | Ability Scores: Characters can decide to use a standard array and divide it onto different scores. Characters can decide to roll 4x6 dice an discard.  Two options.
 x | Random Monster Encounter: Player doesnt meet same monster each time.

## Quick Wins in Existing Code ##
* Implement error handling for unexpected inputs or exceptions in various methods.
* Refactor repetitive code into separate methods for better readability and maintainability.
Done | Create a text based interface for playing the game


### Implementing Additional Game Mechanics ###
* Armor Class (AC) - Does the hit actually land
* Different armor types (light/medium/heavy)
* Equipment slots
* Durability
