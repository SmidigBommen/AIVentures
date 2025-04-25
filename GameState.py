from items import HealingPotion

class GameState:
    def __init__(self, character, MonsterFactory):
        # Setup: Use the provided character and create a monster
        monster_factory = MonsterFactory()
        self.monster_kills = 0

        self.character = character
        #self.monster = monster_factory.create_monster("Baltazar", "Goblin", "Ranger", 1, "Club")

        # Add initial items to the character's inventory
        self.character.add_item(HealingPotion("Small Healing Potion", 10))
        self.character.add_item(HealingPotion("Medium Healing Potion", 25))
