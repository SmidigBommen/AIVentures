from armor import Armor
from equipmentType import EquipmentType
class Entity:
    def __init__(self, name, race, class_name, strength_score, strength_modifier, dexterity_score, dexterity_modifier, constitution_score, constitution_modifier, intelligence_score, intelligence_modifier, wisdom_score, wisdom_modifier, charisma_score, charisma_modifier):
        self.name = name
        self.race = race
        self.class_name = class_name
        self.strength_score = strength_score
        self.strength_modifier = strength_modifier
        self.dexterity_score = dexterity_score
        self.dexterity_modifier = dexterity_modifier
        self.constitution_score = constitution_score
        self.constitution_modifier = constitution_modifier
        self.intelligence_score = intelligence_score
        self.intelligence_modifier = intelligence_modifier
        self.wisdom_score = wisdom_score
        self.wisdom_modifier = wisdom_modifier
        self.charisma_score = charisma_score
        self.charisma_modifier = charisma_modifier
        self.skills = {}
        self.inventory = []
        self.level = 1
        self.xp = 0
        self.max_hit_points = 0
        self.current_hit_points = 0
        self.armor_class = 10
        self.damage_reduction = 0
        self.equipment = {eq_type: None for eq_type in EquipmentType}
        self.skill_proficiencies = set()  
        self.saving_throw_proficiencies = set()
        self.proficiency_bonus = 2  # Default proficiency bonus at level 1

    def get_stats(self):
        stats = (
            f"Name: {self.name}, "
            f"Race: {self.race}, "
            f"Class: {self.class_name}\n"
            f"Strength Score: {self.strength_score}, "
            f"Strength Modifier: {self.strength_modifier}, \n"
            f"Dexterity: {self.dexterity_score}, "
            f"Dexterity Modifier: {self.dexterity_modifier}, \n"
            f"Constitution: {self.constitution_score}, "
            f"Constitution Modifier: {self.constitution_modifier},\n"
            f"Intelligence: {self.intelligence_score}, "
            f"Intelligence Modifier: {self.intelligence_modifier}, \n"
            f"Wisdom: {self.wisdom_score}, "
            f"Wisdom Modifier: {self.wisdom_modifier}, \n"
            f"Charisma: {self.charisma_score}, "
            f"Charisma Modifier: {self.charisma_modifier},\n"
            f"Skills: {self.skills}, "
            f"Inventory: {[item.name for item in self.inventory]}\n"
            f"Level: {self.level}, "
            f"Experience Points: {self.xp}\n"
            f"Hit Points: {self.current_hit_points}/{self.max_hit_points} "
            f"Armor Class: {self.armor_class}, " f"Damage Reduction: {self.damage_reduction}\n"
        )
        return stats

    def heal(self, amount):
        self.current_hit_points = min(self.max_hit_points, self.current_hit_points + amount)
        return amount

    def take_damage(self, amount):
        actual_damage = max(0, amount - self.damage_reduction)
        self.current_hit_points = max(0, self.current_hit_points - actual_damage)
        return actual_damage
    
    def calculate_total_ac(self):
        """Calculate total AC including base AC and dexterity modifier"""
        ac = self.base_ac
        ac += self.dexterity_modifier
        # If character has armor equipped, that would be calculated here
        # For now, we'll just use base + dex modifier
        return ac

    def is_alive(self):
        return self.current_hit_points > 0

    def roll_stats(self):
        # Code to roll for stats
        pass

    def assign_stats(self, strength_score, dexterity_score, constitution_score, intelligence_score, wisdom_score, charisma_score):
        self.strength_score = strength_score
        self.dexterity_score = dexterity_score
        self.constitution_score = constitution_score
        self.intelligence_score = intelligence_score
        self.wisdom_score = wisdom_score
        self.charisma_score = charisma_score

    def add_skill(self, skill, proficiency):
        self.skills[skill] = proficiency

    def add_item(self, item):
        self.inventory.append(item)

    def level_up(self):
        self.level += 1

    def gain_xp(self, xp):
        self.xp += xp
        while self.level < len(self.XP_TABLE) and self.xp >= self.XP_TABLE[self.level]:
            self.level_up()

    def equip(self, item):
        if item.equipment_type in self.equipment:
            self.unequip(item.equipment_type)
            self.equipment[item.equipment_type] = item
            # self.update_stats(item, equip=True)
            print(f"{self.name} has equipped {item.name}.")

    def unequip(self, equipment_type):
        item = self.equipment[equipment_type]
        if item:
            self.update_stats(item, equip=False)
            self.equipment[equipment_type] = None
            print(f"{self.name} has unequipped {item.name}.")

    def update_stats(self, item, equip=True):
        factor = 1 if equip else -1
        self.strength_score += factor * item.strength
        self.dexterity_score += factor * item.dexterity
        self.constitution_score += factor * item.constitution
        self.intelligence_score += factor * item.intelligence
        self.wisdom_score += factor * item.wisdom
        self.charisma_score += factor * item.charisma

    def calculate_armor_class(self):
        ac = 10  # Start with base armor class (AC)
        ac = self.armor_class
        # for equipment in self.equipment.values():
        #     if isinstance(equipment, Armor):
        #         ac += equipment.get_ac_bonus()
        return ac

    def add_skill_proficiency(self, skill_name):
        """Add proficiency in a specific skill"""
        self.skill_proficiencies.add(skill_name)

    def has_skill_proficiency(self, skill_name):
        """Check if entity is proficient in a skill"""
        return skill_name in self.skill_proficiencies

    def add_saving_throw_proficiency(self, ability):
        """Add proficiency in a saving throw"""
        self.saving_throw_proficiencies.add(ability)

    def has_saving_throw_proficiency(self, ability):
        """Check if entity is proficient in a saving throw"""
        return ability in self.saving_throw_proficiencies

    def update_proficiency_bonus(self):
        """Update proficiency bonus based on level"""
        self.proficiency_bonus = 2 + ((self.level - 1) // 4)

    def make_skill_check(self, skill_name, difficulty_class=10):
        """Make a skill check"""
        from skills import make_skill_check
        return make_skill_check(self, skill_name, difficulty_class)
    
    def make_saving_throw(self, ability, difficulty_class=10):
        """Make a saving throw"""
        from dice import Dice
        
        # Get ability modifier
        ability_modifier = getattr(self, f"{ability.lower()}_modifier")
        
        # Add proficiency bonus if proficient
        proficiency_bonus = 0
        if ability in self.saving_throw_proficiencies:
            proficiency_bonus = self.proficiency_bonus
        
        # Roll the dice
        roll = Dice.roll_d20()
        total = roll + ability_modifier + proficiency_bonus
        
        success = total >= difficulty_class
        return {
            "ability": ability,
            "roll": roll,
            "modifier": ability_modifier,
            "proficiency": proficiency_bonus,
            "total": total,
            "dc": difficulty_class,
            "success": success
        }
        
    