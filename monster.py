from entity import Entity
from weaponFactory import WeaponFactory


class Monster(Entity):
    def __init__(self, name, race, class_name, strength_score, strength_modifier, dexterity_score, dexterity_modifier,
                 constitution_score, constitution_modifier, intelligence_score, intelligence_modifier, wisdom_score,
                 wisdom_modifier, charisma_score, charisma_modifier, hit_points, base_ac, damage_reduction,
                 monster_level, weapon_name):
        super().__init__(name, race, class_name, strength_score, strength_modifier, dexterity_score, dexterity_modifier, constitution_score, constitution_modifier, intelligence_score, intelligence_modifier, wisdom_score, wisdom_modifier, charisma_score, charisma_modifier)
        self.max_hit_points = hit_points
        self.current_hit_points = hit_points
        self.base_ac = base_ac  # Store the base AC from race
        self.armor_class = self.calculate_total_ac()  # Calculate total AC including dex modifier
        self.damage_reduction = damage_reduction
        self.level = monster_level
        self.weapon = WeaponFactory().get_weapon_by_name(weapon_name)

    def calculate_total_ac(self):
        """Calculate total AC including base AC and dexterity modifier"""
        ac = self.base_ac
        ac += self.dexterity_modifier
        # If character has armor equipped, that would be calculated here
        return ac

    def take_damage(self, amount):
        self.current_hit_points = max(0, self.current_hit_points - amount)
        return amount

    def is_alive(self):
        return self.current_hit_points > 0

    def assign_stats(self, strength_score, dexterity_score, constitution_score, intelligence_score, wisdom_score, charisma_score):
        self.strength_score = strength_score
        self.dexterity_score = dexterity_score
        self.constitution_score = constitution_score
        self.intelligence_score = intelligence_score
        self.wisdom_score = wisdom_score
        self.charisma_score = charisma_score

    def add_item(self, item):
        self.inventory.append(item)

    def level_up(self):
        self.level += 1

    def gain_xp(self, xp):
        self.xp += xp


    def get_stats(self):
        stats = super().get_stats()
        stats += f"Current Hit Points: {self.current_hit_points}/{self.max_hit_points}\n"
        return stats


