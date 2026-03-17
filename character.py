from dice import Dice
from entity import Entity
from items import HealingPotion
from enum import Enum, auto

class WeaponSlot(Enum):
    MAIN_HAND = auto()
    OFF_HAND = auto()

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
        self.gold = 0
        # Initialize weapon slots
        self.weapon_slots = {
            WeaponSlot.MAIN_HAND: None,
            WeaponSlot.OFF_HAND: None
        }
        # Ability system
        self.power_points = 0
        self.max_power_points = 0
        self.active_effects = []  # list of {"stat", "value", "duration", "source"}

    def assign_stats(self, strength_score, dexterity_score, constitution_score, intelligence_score, wisdom_score, charisma_score):
        self.strength_score = strength_score
        self.dexterity_score = dexterity_score
        self.constitution_score = constitution_score
        self.intelligence_score = intelligence_score
        self.wisdom_score = wisdom_score
        self.charisma_score = charisma_score

    def update_ac(self):
        """Update AC when dexterity or equipment changes"""
        self.armor_class = self.calculate_total_ac()

    def add_skill(self, skill, proficiency):
        self.skills[skill] = proficiency

    def equip_weapon(self, weapon, slot=WeaponSlot.MAIN_HAND):
        """Equip a weapon to a specific slot."""
        if slot not in self.weapon_slots:
            return False

        # Unequip any existing weapon in that slot
        if self.weapon_slots[slot]:
            self.unequip_weapon(slot)

        self.weapon_slots[slot] = weapon

        # If the weapon was in inventory, remove it
        if weapon in self.inventory:
            self.inventory.remove(weapon)

        return True

    def unequip_weapon(self, slot):
        """Unequip a weapon from a specific slot."""
        if slot not in self.weapon_slots or not self.weapon_slots[slot]:
            return False

        weapon = self.weapon_slots[slot]
        self.inventory.append(weapon)
        self.weapon_slots[slot] = None
        return True

    def add_item(self, item):
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

    def gain_xp(self, xp, roll_hp=False):
        """Add XP and auto-level. Returns list of level-up results."""
        self.xp += xp
        results = []
        while self.xp >= self.xp_to_next_level:
            results.append(self.level_up(roll_hp=roll_hp))
        return results

    def level_up(self, roll_hp=False):
        """Level up the character. Returns dict with level-up details.

        Args:
            roll_hp: If True, roll hit die for HP. If False, take average (default).
        """
        self.level += 1
        self.xp -= self.xp_to_next_level
        self.xp_to_next_level = self.calculate_xp_to_next_level()
        self.update_proficiency_bonus()

        con_modifier = self.get_constitution_modifier()

        if roll_hp:
            hit_points_increase = max(1, self.roll_hit_die() + con_modifier)
        else:
            average = (self.hit_die // 2) + 1
            hit_points_increase = max(1, average + con_modifier)

        self.max_hit_points += hit_points_increase

        return {
            "new_level": self.level,
            "hp_increase": hit_points_increase,
            "con_modifier": con_modifier,
            "rolled": roll_hp,
        }


    def roll_hit_die(self):
        return Dice.roll(self.hit_die)

    def get_constitution_modifier(self):
        return (self.constitution_score - 10) // 2

    def get_stats(self):
        stats = super().get_stats()
        stats += f"XP: {self.xp}/{self.xp_to_next_level} Weapon: {self.weapon_slots[WeaponSlot.MAIN_HAND]}\n"
        stats += f"Hit Die: d{self.hit_die}\n"
        stats += f"Skills: {self.skill_proficiencies}\n"
        return stats

    def heal(self, amount):
        self.current_hit_points = min(self.max_hit_points, self.current_hit_points + amount)
        return amount

    def take_damage(self, amount):
        self.current_hit_points = max(0, self.current_hit_points - amount)
        return amount

    def is_alive(self):
        return self.current_hit_points > 0

