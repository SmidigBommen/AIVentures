import random

from character import WeaponSlot
from dice import Dice
from equipmentType import EquipmentType
from lootGenerator import LootGenerator


class Battle:
    def __init__(self, character, monster):
        self.character = character
        self.monster = monster
        self.round_count = 0

    def calculate_initiative(self):
        initiative = [
            (self.character.name, self.character.dexterity_score + Dice.roll_d20()),
            (self.monster.name, self.monster.dexterity_score + Dice.roll_d20())
        ]
        result = sorted(initiative, key=lambda x: x[1], reverse=True)
        print("Initiative rolls: ", result)
        return result

    def player_turn(self):
        print(f"\n{self.character.name}'s turn!")
        while True:
            action = input("Do you want to\n(a)ttack, (d)efend or (u)se an item? ").lower()
            if action == 'a':
                return self.player_attack()
            elif action == 'd':
                return self.player_defend()
            elif action == 'u':
                return self.player_use_item()
            else:
                print("Invalid action. Please choose 'a', 'd' or 'u'.")

    def player_use_item(self):
        usable_items = self.character.get_usable_items()
        if not usable_items:
            print("You have no usable items!")
            return self.player_turn()

        print("Available items:")
        for i, item in enumerate(usable_items):
            print(f"{i + 1}. {item.name} - {item.description}")

        while True:
            choice = input("Choose an item to use (or 'c' to cancel): ")
            if choice.lower() == 'c':
                return self.player_turn()
            try:
                item_index = int(choice) - 1
                if 0 <= item_index < len(usable_items):
                    chosen_item = usable_items[item_index]
                    if self.character.use_item(chosen_item):
                        return "use_item", chosen_item.name
                    else:
                        print("Failed to use the item. Please try again.")
                else:
                    print("Invalid item number. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number or 'c' to cancel.")

    def monster_turn(self):
        print(f"\n{self.monster.name}'s turn!")
        random_choice = random.random()
        if random_choice < 0.7:  # 70% chance to attack
            return self.monster_attack()
        elif random_choice < 0.9:  # 20% chance to defend
            return self.monster_defend()
        else:  # 10% chance to use special ability
            return self.monster_special_ability()

    def player_attack(self):
        weapon = self.character.weapon_slots[WeaponSlot.MAIN_HAND]
        if weapon:
            ability_mod = self.character.get_attack_modifier(weapon)
        else:
            ability_mod = self.character.strength_modifier

        # To hit roll
        attack_roll = Dice.roll_d20() + ability_mod + self.character.proficiency_bonus
        print(f"\n{self.character.name} (mod {ability_mod}, prof +{self.character.proficiency_bonus}) rolls {attack_roll} to hit against AC {self.monster.armor_class}")

        if attack_roll >= self.monster.armor_class:
            if weapon:
                damage = 0
                for _ in range(weapon.damage_dice_count):
                    roll = Dice.roll(weapon.damage_die)
                    damage += roll
                    print(f"{self.character.name} rolls {roll} damage")
            else:
                damage = Dice.roll_d6()

            actual_damage = max(1, damage + ability_mod)
            self.monster.take_damage(actual_damage)
            print(f"{self.character.name} hit {self.monster.name} for {actual_damage} damage!")
        else:
            actual_damage = 0
            print(f"{self.character.name}'s attack missed!")
        return attack_roll, actual_damage

    def monster_attack(self):
        weapon = self.monster.weapon
        ability_mod = self.monster.get_attack_modifier(weapon)

        attack_roll = Dice.roll_d20() + ability_mod + self.monster.proficiency_bonus
        print(f"{self.monster.name} (mod {ability_mod}, prof +{self.monster.proficiency_bonus}) rolls {attack_roll} to hit against AC {self.character.armor_class}")

        if attack_roll >= self.character.armor_class:
            damage = 0
            for _ in range(weapon.damage_dice_count):
                damage += Dice.roll(weapon.damage_die)
            damage_dealt = max(1, damage + ability_mod)
            actual_damage = self.character.take_damage(damage_dealt)
            print(f"{self.monster.name} hit {self.character.name} for {actual_damage} damage!")
        else:
            actual_damage = 0
            print(f"{self.monster.name}'s attack missed!")
        return attack_roll, actual_damage

    def player_defend(self):
        defense_bonus = Dice.roll_d4()
        self.character.armor_class += defense_bonus
        print(f"{self.character.name} takes a defensive stance, gaining +{defense_bonus} to Armor Class this round!")
        return "defend", defense_bonus

    def monster_defend(self):
        defense_bonus = Dice.roll_d4()
        self.monster.armor_class += defense_bonus
        print(f"{self.monster.name} takes a defensive stance, gaining +{defense_bonus} to Armor Class this round!")
        return "defend", defense_bonus

    def player_special_ability(self):
        # Placeholder for special ability implementation
        print(f"{self.character.name} uses a special ability!")
        return "special", 0

    def monster_special_ability(self):
        # Placeholder for special ability implementation
        print(f"{self.monster.name} uses a special ability!")
        return "special", 0

    def check_victory(self):
        if not self.character.is_alive():
            return self.monster.name
        elif not self.monster.is_alive():
            return self.character.name
        else:
            return None

    def run_battle(self):
        print(f"\033[35mBattle begins:\033[97m {self.character.name} ({self.character.level}) vs {self.monster.name} {self.monster.race} ({self.monster.level})")
        initiative = self.calculate_initiative()

        while True:
            self.round_count += 1
            print(f"\n--- Round {self.round_count} ---")
            print(f"{self.character.name}'s HP: {self.character.current_hit_points}/{self.character.max_hit_points}")
            print(f"{self.monster.name}'s HP: {self.monster.current_hit_points}/{self.monster.max_hit_points}")

            for name, _ in initiative:
                if name == self.character.name:
                    action = self.player_turn()
                    if action[0] == "use_item":
                        print(f"{self.character.name} used {action[1]}!")
                else:
                    self.monster_turn()

                winner = self.check_victory()
                if winner:
                    return self.end_battle(winner == self.character.name)

            # Reset temporary defensive bonuses
            #self.character.armor_class = self.character.base_armor_class
            self.monster.armor_class = self.monster.base_ac

    def end_battle(self, character_won):
        if character_won:
            xp_award = self.calculate_xp_award()
            print(f"\033[35m {self.character.name} has won the battle and gained {xp_award} experience points!\033[97m")
            self.character.gain_xp(xp_award)

            # Calculate and award gold
            gold_award = self.calculate_gold_award()
            self.character.gold += gold_award

            # Chance for item drop
            loot = LootGenerator().generate_loot(self.monster.level, self.character.level)
            if loot:
                if loot["type"] == "gold":
                    self.character.gold += loot["amount"]
                else:
                    self.character.add_item(loot["item"])
                print(f"You found: {loot['message']}!")
            else:
                print("You found no loot.")
            return "player"
        else:
            return "monster"

    def calculate_xp_award(self):
        # Example: Award XP based on the monster's level and the number of rounds
        base_xp = 100 * self.monster.level
        round_bonus = max(0, 10 * (10 - self.round_count))  # Bonus for quick victories
        return base_xp + round_bonus

    def calculate_gold_award(self):
        # Base gold based on monster level with some randomness
        base_gold = self.monster.level * 5
        return base_gold + Dice.roll_d8()

    def generate_loot(self):
        return LootGenerator().generate_loot(self.monster.level, self.character.level)