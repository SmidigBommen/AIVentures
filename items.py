class Item:
    def __init__(self, name, description, is_usable_in_battle=True):
        self.name = name
        self.description = description
        self.is_usable_in_battle = is_usable_in_battle

    def use(self, character):
        raise NotImplementedError("This method should be implemented by subclasses")

class QuestItem(Item):
    def __init__(self, name, description, quest_id):
        super().__init__(name, description, is_usable_in_battle=False)
        self.quest_id = quest_id

    def use(self, character):
        pass


class HealingPotion(Item):
    def __init__(self, name, healing_amount):
        super().__init__(name, f"Heals {healing_amount} hit points")
        self.healing_amount = healing_amount

    def use(self, character):
        return character.heal(self.healing_amount)