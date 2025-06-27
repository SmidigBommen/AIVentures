import json
import random
import os
from GameState import GameState
from battleAI import Battle
from monsterFactory import MonsterFactory
from charactercreator import CharacterCreator
from shop import Shop
from shopUI import ShopUI
gamestate = GameState()

def clear_screen():
    """Clear the terminal screen."""
    # For Windows
    if os.name == 'nt':
        _ = os.system('cls')
    # For macOS and Linux
    else:
        _ = os.system('clear')


def display_introduction(campaign):
    color_MAGENTA = "\033[35m"
    color_CYAN = "\033[36m"
    color_YELLOW = "\033[33m"
    color_WHITE = "\033[97m"

    clear_screen()
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

    return monster_factory.create_monster(monster_name, monster_race, monster_class, monster_level, "Club")


def post_battle_menu():
    """Display options after winning a battle"""
    print("\n" + "=" * 50)
    print("What would you like to do next?")
    print("1. Continue exploring (chance for another encounter)")
    print("2. Rest and recover (restore some HP)")
    print("3. Return to the safety of the town")
    print("4. View inventory")
    print("5. View character stats")
    print("6. Quit game")

    choice = input("Enter your choice (1-6): ")
    clear_screen()

    if choice == "1":
        # Continue exploring with chance for encounter
        if random.random() < 0.7:  # 70% chance for encounter
            print("\nYou encounter a monster while exploring!")
            # Create a new monster appropriate for location and level
            gamestate.monster = create_monster_for_location(gamestate.current_location, gamestate.character.level)
            return "battle"
        else:
            print("\nYou explore the area but find nothing of interest.")
            return "idle"  # Return to idle instead of recursively calling post_battle_menu

    elif choice == "2":
        # Rest and recover some HP
        recovery = (gamestate.character.hit_die // 2) + gamestate.character.constitution_modifier
        recovery = max(1, recovery)
        gamestate.character.heal(recovery)
        print(f"\nYou take a short rest and recover {recovery} hit points.")
        print(f"Current HP: {gamestate.character.current_hit_points}/{gamestate.character.max_hit_points}")
        return "idle"  # Return to idle

    elif choice == "3":
        # Return to idle state in town location
        gamestate.current_location = gamestate.act["locations"][0]
        for location in gamestate.act["locations"]:
            ## move the player back to town
            if location["type"] == "town":
                gamestate.current_location = location
                return "idle"
        return "idle"

    elif choice == "4":
        # View inventory
        print("\n--- Inventory ---")
        if not gamestate.character.inventory:
            print("Your inventory is empty.")
        else:
            for i, item in enumerate(gamestate.character.inventory):
                print(f"{i + 1}. {item.name} - {item.description}")
        return post_battle_menu()

    elif choice == "5":
        # View character stats
        print("\n--- Character Stats ---")
        print(gamestate.character.get_stats() + "\n")
        return post_battle_menu()

    elif choice == "6":
        # Quit game
        print("\nThank you for playing!")
        return "quit"

    else:
        print("\nInvalid choice. Please try again.")
        return post_battle_menu()


def display_locations():
    print("\n" + "=" * 50)
    print("Available Locations:")
    for i, location in enumerate(gamestate.act["locations"], 1):
        print(f"{i}. {location['name']} - {location['description']}")

def display_areas():
    print("\n" + "=" * 50)
    print("You explore your surroundings and find:")
    for i, area in enumerate(gamestate.current_location["areas"], 1):
        print(f"{i}. {area['name']} - {area['description']}")



## ----------    Main    ----------
def main():
    # Setup Campaign
    global gamestate
    current_campaign = setup_campaign()
    town_shop = Shop("Rivermeet General Store")
    shop_ui = ShopUI(town_shop)

    creator = CharacterCreator()
    gamestate.add_player(creator.create_character())

    gamestate.state = "idle"  # Initial state

    while gamestate.state != "quit":
        if gamestate.state == "idle":
            gamestate.state = idle_menu()

        elif gamestate.state == "enter_areas":
            print(f"\n--- {gamestate.current_location['name']} ---")
            print(gamestate.current_location['description'])
            # Initialize area exploration
            if not gamestate.current_area:
                # Set starting area for the location
                starting_area_id = gamestate.current_location.get("starting_area", gamestate.current_location["areas"][0]["id"])
                gamestate.set_current_area(starting_area_id)
            gamestate.state = "area_menu"

        elif gamestate.state == "area_menu":
            gamestate.state = area_menu()
            # Generate a monster encounter based on location
            #gamestate.monster = create_monster_for_location(gamestate.current_location, gamestate.character.level)
            #gamestate.state = "battle"

        elif gamestate.state == "battle":
            battle = Battle(gamestate.character, gamestate.monster)
            winner = battle.run_battle()

            if winner == "player":
                print(f"Victory! You defeated {gamestate.monster.name}!")
                gamestate.state = post_battle_menu()
            elif winner == "monster":
                print(f"Game Over! {gamestate.character.name} has been defeated...")
                gamestate.state = "quit"

        elif gamestate.state == "change_location":
            display_locations()
            travel_location = input("Enter your choice: ")
            clear_screen()
            if travel_location == "1":
                gamestate.current_location = gamestate.act["locations"][0]
                gamestate.state = "idle"
            elif travel_location == "2":
                gamestate.current_location = gamestate.act["locations"][1]
                gamestate.state = "idle"
            elif travel_location == "3":
                gamestate.current_location = gamestate.act["locations"][2]
                gamestate.state = "idle"
            else:
                print("Invalid choice. Please try again.")
                gamestate.state = "change_location"

            gamestate.state = "idle"

        elif gamestate.state == "shop":
            print("You enter the local shop...")
            shop_ui.show_shop_menu(gamestate.character)
            gamestate.state = "idle"  # Return to idle state after shopping
## ------------------------------------

def setup_campaign():
    with open("json/campaign.json") as f:
        campaign = json.load(f)
    display_introduction(campaign)
    # Find the starting location data
    gamestate.act = campaign["acts"][0]
    current_act = gamestate.act  # starting act 1
    start_location_name = campaign["startingLocation"]
    gamestate.current_location = None
    for location in current_act["locations"]:
        if location["name"] == start_location_name:
            gamestate.current_location = location
            break
    return campaign


def idle_menu():
    print("\n" + "=" * 50)
    print(f"You are in {gamestate.current_location['name']} - {gamestate.current_location['type']} ")
    print("\nWhat would you like to do?")
    print("1. Explore the area (chance for an encounter)")

    # Only show shop option in towns
    if gamestate.current_location["type"] == "town":
        print("2. Visit the shop")
        print("3. Rest at the inn (restore full HP for 5 gold)")
    else:
        print("2. Set up camp (restore some HP)")

    print("4. View inventory")
    print("5. View character stats")
    print("6. Travel to another location")
    print("7. Quit game")

    choice = input("Enter your choice: ")
    clear_screen()

    if choice == "1":
        return "enter_areas"
    elif choice == "2":
        if gamestate.current_location["type"] == "town":
            return "shop"
        else:
            resting()
            return "idle"
    elif choice == "3" and gamestate.current_location["type"] == "town":
        # Inn rest - restore full HP for gold
        cost = 5  # Gold cost to rest
        if gamestate.character.gold >= cost:
            gamestate.character.gold -= cost
            gamestate.character.current_hit_points = gamestate.character.max_hit_points
            print(f"\nYou rest at the inn for {cost} gold and recover fully.")
            print(f"Current HP: {gamestate.character.current_hit_points}/{gamestate.character.max_hit_points}")
        else:
            print(f"\nYou don't have enough gold to rest at the inn. You need {cost} gold.")
        return "idle"
    elif choice == "4":
        # View inventory
        print("\n--- Inventory ---")
        if not gamestate.character.inventory:
            print("Your inventory is empty.")
        else:
            for i, item in enumerate(gamestate.character.inventory):
                print(f"{i + 1}. {item.name} - {item.description}")
        return idle_menu()  # Return to idle menu
    elif choice == "5":
        # View character stats
        print("\n--- Character Stats ---")
        print(f"{gamestate.character}")
        print(gamestate.character.get_stats() + "\n")
        return idle_menu()  # Return to idle menu
    elif choice == "6":
        # Travel to another location
        return "change_location"
    elif choice == "7":
        # Quit game
        print("\nThank you for playing!")
        return "quit"
    else:
        print("\nInvalid choice. Please try again.")
        return idle_menu()


def explore_area():
    """Handle exploration within the current area"""
    if not gamestate.current_area:
        print("No area to explore!")
        return "idle"

    area = gamestate.current_area
    print(f"\n--- Exploring {area['name']} ---")
    print(area['description'])

    # Check if this area has encounters
    encounter_chance = area.get('encounters', 0)
    if encounter_chance > 0:
        # Roll for encounter based on area's encounter level
        import random
        if random.random() < (encounter_chance * 0.2):  # 20% per encounter level
            print(f"\nYou encounter danger in {area['name']}!")
            gamestate.monster = create_monster_for_location(gamestate.current_location, gamestate.character.level)
            return "battle"

    print(f"\nYou explore {area['name']} but find nothing threatening.")
    return "area_menu"


def area_menu():
    """Menu for actions within a specific area"""
    area = gamestate.current_area
    print(f"\n--- {area['name']} ---")
    print(area['description'])
    print("\nWhat would you like to do?")
    print("1. Explore this area (chance for encounter)")
    print("2. Move to a connected area")
    print("3. Return to location overview")
    print("4. View character stats")

    choice = input("Enter your choice: ")
    clear_screen()

    if choice == "1":
        return explore_area()
    elif choice == "2":
        return navigate_to_connected_area()
    elif choice == "3":
        return "idle"
    elif choice == "4":
        print("\n--- Character Stats ---")
        print(gamestate.character.get_stats())
        return area_menu()
    else:
        print("Invalid choice. Please try again.")
        return area_menu()


def navigate_to_connected_area():
    """Allow player to move to areas connected to the current area"""
    current_area = gamestate.current_area

    if not current_area or not current_area.get('connections'):
        print("There are no connected areas to move to.")
        return area_menu()

    # Get all areas in the current location for lookup
    areas_by_id = {area["id"]: area for area in gamestate.current_location["areas"]}

    print(f"\nFrom {current_area['name']}, you can move to:")
    connected_areas = []

    for i, connection_id in enumerate(current_area['connections'], 1):
        if connection_id in areas_by_id:
            connected_area = areas_by_id[connection_id]
            connected_areas.append(connected_area)
            print(f"{i}. {connected_area['name']} - {connected_area['description']}")
        else:
            print(f"Warning: Connection {connection_id} not found!")

    if not connected_areas:
        print("No valid connections found.")
        return area_menu()

    print(f"{len(connected_areas) + 1}. Stay in {current_area['name']}")

    while True:
        try:
            choice = int(input(f"\nWhere would you like to go? (1-{len(connected_areas) + 1}): "))

            if choice == len(connected_areas) + 1:
                # Stay in current area
                return area_menu()
            elif 1 <= choice <= len(connected_areas):
                # Move to selected area
                selected_area = connected_areas[choice - 1]
                gamestate.current_area = selected_area
                print(f"\nYou move to {selected_area['name']}.")

                # Check for automatic encounters when entering certain areas
                if selected_area.get('encounters', 0) >= 4:  # High encounter areas
                    import random
                    if random.random() < 0.3:  # 30% chance for immediate encounter
                        print("As you enter, you're immediately confronted by danger!")
                        gamestate.monster = create_monster_for_location(gamestate.current_location,
                                                                        gamestate.character.level)
                        return "battle"

                return area_menu()
            else:
                print(f"Please enter a number between 1 and {len(connected_areas) + 1}.")
        except ValueError:
            print("Please enter a valid number.")

def resting():
    # Camp rest - restore some HP
    recovery = (gamestate.character.hit_die // 2) + gamestate.character.constitution_modifier
    recovery = max(1, recovery)
    gamestate.character.heal(recovery)
    print(f"\nYou set up camp and recover {recovery} hit points.")
    print(f"Current HP: {gamestate.character.current_hit_points}/{gamestate.character.max_hit_points}")


if __name__ == "__main__":
    main()