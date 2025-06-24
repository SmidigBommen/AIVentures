from items import HealingPotion

class GameState:
    state = "idle"
    campaign = None
    act = ""
    current_location = None
    monster_kills = 0
    character = None
    monster_factory = None

    def add_player(self, player):
        self.character = player
        # Add initial items to the character's inventory
        self.character.add_item(HealingPotion("Small Healing Potion", 10))
        self.character.add_item(HealingPotion("Medium Healing Potion", 25))




    def check_skill(self,skill_name, difficulty_class=10):
        result = self.character.make_skill_check(skill_name, difficulty_class)
        print(f"{self.character.name} rolled {result['roll']} for {skill_name} and got a {result['total']} total.")

        if result['success']:
            print(f"{self.character.name} has succeeded with {skill_name}!")
        else:
            print(f"{self.character.name} failed with {skill_name}.")

        return result