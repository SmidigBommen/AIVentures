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
        # Check if the slot is valid
        if slot not in self.weapon_slots:
            print(f"Invalid weapon slot: {slot}")
            return False

        # Unequip any existing weapon in that slot
        if self.weapon_slots[slot]:
            self.unequip_weapon(slot)

        # Equip the new weapon
        self.weapon_slots[slot] = weapon

        # Apply the weapon's bonuses if needed
        # This depends on how your weapon bonuses work

        # If the weapon was in inventory, remove it
        if weapon in self.inventory:
            self.inventory.remove(weapon)

        print(f"{self.name} equipped {weapon.name} in {slot.name}")
        return True

    def unequip_weapon(self, slot):
        """Unequip a weapon from a specific slot."""
        if slot not in self.weapon_slots or not self.weapon_slots[slot]:
            print(f"No weapon equipped in {slot.name}")
            return False

        weapon = self.weapon_slots[slot]

        # Add the weapon back to inventory
        self.inventory.append(weapon)

        # Clear the slot
        self.weapon_slots[slot] = None

        print(f"{self.name} unequipped {weapon.name}")
        return True

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
        while self.xp >= self.xp_to_next_level:
            self.level_up()

    def level_up(self):
        self.level += 1
        self.xp -= self.xp_to_next_level
        self.xp_to_next_level = self.calculate_xp_to_next_level()
        self.update_proficiency_bonus()
        print(f"{self.name} has leveled up to level {self.level} \n")

        # Update constitution modifier as it might have changed
        con_modifier = self.get_constitution_modifier()
        print(f"Your hit points can increase by a maximum of {self.hit_die}+{con_modifier}")
        choice = input("Would you like to (r)oll for points or take the (a)verage? ").lower()

        if choice == 'r':
            # Roll for hit points
            hit_points_increase = self.roll_hit_die() + con_modifier
            # Ensure at least 1 hit point gained per level
            hit_points_increase = max(1, hit_points_increase)
            print(f"You rolled a {hit_points_increase - con_modifier} + {con_modifier} (CON mod)")
        else:
            # Take average
            average = (self.hit_die // 2) + 1  # This is the 5e way to calculate average
            hit_points_increase = average + con_modifier
            print(f"You took the average: {average} + {con_modifier} (CON mod)")

        self.max_hit_points += hit_points_increase
        print(f"Hit Points increased by {hit_points_increase}")


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

