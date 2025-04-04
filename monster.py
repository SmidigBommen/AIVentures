from entity import Entity

class Monster(Entity):
    def __init__(self, name, race, class_name, strength, dexterity, constitution, intelligence, wisdom, charisma,
                 hit_points, base_ac, damage_reduction, monster_level):
        super().__init__(name, race, class_name, strength, dexterity, constitution, intelligence, wisdom, charisma)
        self.max_hit_points = hit_points
        self.current_hit_points = hit_points
        self.base_ac = base_ac  # Store the base AC from race
        self.armor_class = self.calculate_total_ac()  # Calculate total AC including dex modifier
        self.damage_reduction = damage_reduction
        self.level = monster_level

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

    def take_damage(self, amount):
        self.current_hit_points = max(0, self.current_hit_points - amount)
        return amount

    def is_alive(self):
        return self.current_hit_points > 0
    def roll_stats(self):
        # Code to roll for stats
        pass

    def assign_stats(self, strength, dexterity, constitution, intelligence, wisdom, charisma):
        self.strength = strength
        self.dexterity = dexterity
        self.constitution = constitution
        self.intelligence = intelligence
        self.wisdom = wisdom
        self.charisma = charisma

    def add_skill(self, skill, proficiency):
        self.skills[skill] = proficiency

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
