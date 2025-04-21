import json
import random
from GameState import GameState
from battleAI import Battle
from monsterFactory import MonsterFactory
from charactercreator import CharacterCreator


def display_introduction(campaign):
    color_MAGENTA = "\033[35m"
    color_CYAN = "\033[36m"
    color_YELLOW = "\033[33m"
    color_WHITE = "\033[97m"

    print("\n" + "=" * 40)
    print(color_MAGENTA + f"\n{campaign['title'].upper()}" + color_WHITE)
    print("=" * 40 + "\n")

    # Display the campaign description with better formatting
    print(color_WHITE + campaign["description"] + "\n")

    # Add narrative introduction
    print(color_CYAN + "The sun sets on another day in Eldoria as you arrive in Rivermeet Town.")
    print("Strange rumors have been circulating about unusual occurrences in the region.")
    print("The once peaceful kingdom now feels uneasy, as if darkness is growing..." + color_WHITE)

    # Display villain info for context
    print(color_YELLOW + f"\nDanger lurks in the shadows...")
    print(f"It is said that {campaign['villain']['name']} plots against the realm.")
    print(campaign['villain']['description'] + color_WHITE + "\n")

    input("Press Enter to begin your adventure...")


def create_monster_for_location(location, character_level):
    monster_factory = MonsterFactory()

    # Extract encounter level range from location
    level_range = location.get("encounterLevel", "1-1")
    min_level, max_level = map(int, level_range.split("-"))

    # Adjust based on character level, but keep within location range
    monster_level = min(max(character_level, min_level), max_level)

    # Select a monster type based on location
    if location["type"] == "wilderness":
        monster_types = [("Goblin", "Ranger"), ("Orc", "Barbarian")]
    elif location["type"] == "dungeon":
        monster_types = [("Goblin", "Rogue"), ("Troll", "Fighter")]
    else:  # town or default
        monster_types = [("Goblin", "Rogue")]

    monster_race, monster_class = random.choice(monster_types)

    # Generate a random name
    monster_names = ["Grak", "Thurg", "Zort", "Morg", "Kruzz", "Azgul"]
    monster_name = random.choice(monster_names)

    return monster_factory.create_monster(monster_name, monster_race, monster_class, monster_level)


def post_battle_menu(gamestate, current_location):
    """Display options after winning a battle"""
    print("\n" + "=" * 50)
    print("What would you like to do next?")
    print("1. Continue exploring (chance for another encounter)")
    print("2. Rest and recover (restore some HP)")
    print("3. View inventory")
    print("4. Move to a different location")
    print("5. Visit the shop (if in a town)")
    print("6. View character stats")
    print("7. Quit game")

    choice = input("Enter your choice (1-7): ")

    if choice == "1":
        # Continue exploring with chance for encounter
        if random.random() < 0.7:  # 70% chance for encounter
            print("\nYou encounter a monster while exploring!")
            # Create a new monster appropriate for location and level
            gamestate.monster = create_monster_for_location(current_location, gamestate.character.level)
            return "battle"
        else:
            print("\nYou explore the area but find nothing of interest.")
            return post_battle_menu(gamestate, current_location)

    elif choice == "2":
        # Rest and recover some HP
        recovery = gamestate.character.hit_die // 2 + gamestate.character.constitution_modifier
        recovery = max(1, recovery)
        gamestate.character.heal(recovery)
        print(f"\nYou take a short rest and recover {recovery} hit points.")
        print(f"Current HP: {gamestate.character.current_hit_points}/{gamestate.character.max_hit_points}")
        return "explore"

    elif choice == "3":
        # View inventory
        print("\n--- Inventory ---")
        if not gamestate.character.inventory:
            print("Your inventory is empty.")
        else:
            for i, item in enumerate(gamestate.character.inventory):
                print(f"{i + 1}. {item.name} - {item.description}")
        return post_battle_menu(gamestate, current_location)

    elif choice == "4":
        # Move to a different location - We'll implement this next
        print("\nMoving to a different location...")
        return "change_location"

    elif choice == "5":
        # Visit shop (if in a town)
        if current_location["type"] == "town":
            print("\nVisiting the shop...")
            # We'll implement shop functionality later
            return "shop"
        else:
            print("\nThere are no shops in this area. You must be in a town to visit shops.")
            return post_battle_menu(gamestate, current_location)

    elif choice == "6":
        # View character stats
        print("\n--- Character Stats ---")
        print(gamestate.character.get_stats())
        return post_battle_menu(gamestate, current_location)

    elif choice == "7":
        # Quit game
        print("\nThank you for playing!")
        return "quit"

    else:
        print("\nInvalid choice. Please try again.")
        return post_battle_menu(gamestate, current_location)


def main():
    # Setup Campaign
    with open("campaign.json") as f:
        campaign = json.load(f)
    display_introduction(campaign)
    # Find the starting location data
    current_act = campaign["acts"][0]  # starting act 1
    start_location_name = campaign["startingLocation"]
    current_location = None
    for location in current_act["locations"]:
        if location["name"] == start_location_name:
            current_location = location
            break

    # Create a game state
    creator = CharacterCreator()
    player = creator.create_character()
    # Add gold to character (we'll need to add this property to Character class)
    player.gold = 50  # Starting gold

    gamestate = GameState(player, MonsterFactory)
    # Main game loop
    game_state = "explore"  # Initial state
    while game_state != "quit":
        if game_state == "explore":
            print(f"\n--- {current_location['name']} ---")
            print(current_location['description'])

            # Generate a monster encounter based on location
            gamestate.monster = create_monster_for_location(current_location, gamestate.character.level)
            game_state = "battle"

        elif game_state == "battle":
            battle = Battle(gamestate.character, gamestate.monster)
            winner = battle.run_battle()

            if winner == "player":
                print(f"Victory! You defeated {gamestate.monster.name}!")
                game_state = post_battle_menu(gamestate, current_location)
            elif winner == "monster":
                print(f"Game Over! {gamestate.character.name} has been defeated...")
                game_state = "quit"

        elif game_state == "change_location":
            # We'll implement location changing in the next step
            game_state = "explore"

        elif game_state == "shop":
            # We'll implement shop functionality in a future step
            print("Shop functionality coming soon!")
            game_state = "explore"

if __name__ == "__main__":
    main()