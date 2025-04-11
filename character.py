from dice import Dice
from entity import Entity
from items import HealingPotion


class Character(Entity):
    def __init__(self, name, race, class_name, strength_score, strength_modifier, dexterity_score, dexterity_modifier, constitution_score, constitution_modifier, intelligence_score, intelligence_modifier, wisdom_score, wisdom_modifier, charisma_score, charisma_modifier, hit_points, base_ac, damage_reduction):
        super().__init__(name, race, class_name, strength_score, strength_modifier, dexterity_score, dexterity_modifier, constitution_score, constitution_modifier, intelligence_score, intelligence_modifier, wisdom_score, wisdom_modifier, charisma_score, charisma_modifier)
        self.max_hit_points = hit_points
        self.current_hit_points = hit_points
        self.base_ac = base_ac #Store the base AC from race
        self.armor_class = self.calculate_total_ac()  #Calculate total AC including dex modifier
        self.damage_reduction = damage_reduction
        self.inventory = []
        self.level = 1
        self.xp = 0
        self.xp_to_next_level = self.calculate_xp_to_next_level()
        self.hit_die = 8  # Default hit die, will be overridden by CharacterFactory

    def assign_stats(self, strength_score, dexterity_score, constitution_score, intelligence_score, wisdom_score, charisma_score):
        self.strength_score = strength_score
        self.dexterity_score = dexterity_score
        self.constitution_score = constitution_score
        self.intelligence_score = intelligence_score
        self.wisdom_score = wisdom_score
        self.charisma_score = charisma_score

    def calculate_dexterity_modifier(self):
        """Calculate the Dexterity modifier using D&D 5e rules"""
        return (self.dexterity - 10) // 2

    def calculate_total_ac(self):
        """Calculate total AC including base AC and dexterity modifier"""
        ac = self.base_ac
        # Add dexterity modifier to AC
        ac += self.calculate_dexterity_modifier()
        # If character has armor equipped, that would be calculated here
        # For now, we'll just use base + dex modifier
        return ac

    def update_ac(self):
        """Update AC when dexterity or equipment changes"""
        self.armor_class = self.calculate_total_ac()

    def add_skill(self, skill, proficiency):
        self.skills[skill] = proficiency

    def add_item(self, item):
        item.is_usable_in_battle = True
        self.inventory.append(item)

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)

    def use_item(self, item):
        if item in self.inventory:
            if isinstance(item, HealingPotion):
                item.use(self)
                self.heal(item.healing_amount)
                self.remove_item(item)
                return True

        return False

    def get_usable_items(self):
        return [item for item in self.inventory if item.is_usable_in_battle]

    def calculate_xp_to_next_level(self):
        return self.level * 150  # Simple calculation, can be adjusted for balance

    def gain_xp(self, xp):
        self.xp += xp
        print(f"{self.name} gained {xp} XP!")
        while self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.xp -= self.xp_to_next_level
        self.xp_to_next_level = self.calculate_xp_to_next_level()

        # Increase stats - Can be changed later to be class specific
        # self.strength_score += Dice.roll_d4()
        # self.dexterity += Dice.roll_d4()
        # self.constitution += Dice.roll_d4()
        # self.intelligence += Dice.roll_d4()
        # self.wisdom += Dice.roll_d4()
        # self.charisma += Dice.roll_d4()

        # Update constitution modifier as it might have changed
        con_modifier = self.get_constitution_modifier()

        # Increase hit points based on character's hit die and constitution modifier
        hit_points_increase = self.roll_hit_die() + con_modifier

        # Ensure at least 1 hit point gained per level
        hit_points_increase = max(1, hit_points_increase)

        self.max_hit_points += hit_points_increase

        # Increase hit points - old way of calculating based on a d8 die for all classes
        #hit_points_increase = Dice.roll_d8() + self.get_constitution_modifier()
        #self.max_hit_points += hit_points_increase
        #self.current_hit_points += hit_points_increase

        print(f"{self.name} has leveled up to level {self.level}!")
        print(f"Hit Points increased by {hit_points_increase}")
        print("All attributes have increased!")

    def roll_hit_die(self):
        if self.hit_die == 6:
            return Dice.roll_d6()
        elif self.hit_die == 8:
            return Dice.roll_d8()
        elif self.hit_die == 10:
            return Dice.roll_d10()
        elif self.hit_die == 12:
            return Dice.roll_d12()
        else:
            # Default to d8 if something went wrong
            return Dice.roll_d8()

    def get_constitution_modifier(self):
        return (self.constitution - 10) // 2

    def get_stats(self):
        stats = super().get_stats()
        stats += f"Level: {self.level} "
        stats += f"XP: {self.xp}/{self.xp_to_next_level} "
        stats += f"Current Hit Points: {self.current_hit_points}/{self.max_hit_points}\n"
        stats += f"Hit Die: d{self.hit_die}\n"
        return stats

    def heal(self, amount):
        self.current_hit_points = min(self.max_hit_points, self.current_hit_points + amount)
        return amount

    def take_damage(self, amount):
        self.current_hit_points = max(0, self.current_hit_points - amount)
        return amount

    def is_alive(self):
        return self.current_hit_points > 0
