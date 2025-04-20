import json

from GameState import GameState
from battleAI import Battle
from monsterFactory import MonsterFactory
from charactercreator import CharacterCreator


def display_introduction(campaign):
    color_MAGENTA = "\033[35m"
    color_CYAN = "\033[36m"
    color_YELLOW = "\033[33m"
    color_WHITE = "\033[97m"

    print("\n" + "=" * 60)
    print(color_MAGENTA + f"\n{campaign['title'].upper()}" + color_WHITE)
    print("=" * 60 + "\n")

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


def main():
    # Setup Campaign
    with open("campaign.json") as f:
        campaign = json.load(f)
    display_introduction(campaign)

    # Create a game state
    creator = CharacterCreator()
    player = creator.create_character()
    gamestate = GameState(player, MonsterFactory)

    # Main loop
    playing = True # TODO: Add more states later (CREATOR, IDLE, BATTLE, ENDING
    while playing:
        gamestate.monster.level = gamestate.character.level

        # Get user input
        command = input("\nWhat would you like to do? (a)ttack,(s)tats or (q)uit: ")

        # Process input
        if command.lower() == "a":
            battle = Battle(gamestate.character, gamestate.monster)
            winner = battle.run_battle()

            if winner == "player":
                print(f"Victory! You defeated {gamestate.monster.name}!")
                gamestate.monster_kills += 1
                # Creating a new monster for next round (temporary shortcut for keeping the game going)
                monster = MonsterFactory().create_monster("Baltazar2", "Goblin",
                                                          "Ranger",2)
                gamestate.monster = monster
                playing = True
            elif winner == "monster":
                print(f"Game Over! {gamestate.character.name} has been defeated...")
                playing = False
        elif command.lower() == "s":
            print("\n---- Current State ----")
            print(gamestate.character.get_stats())
            print(gamestate.monster.get_stats())
        elif command.lower() == "q":
            print("Goodbye!")
            playing = False
        else:
            print("Invalid command. Please try again.")

if __name__ == "__main__":
    main()