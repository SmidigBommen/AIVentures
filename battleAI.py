import random
from dice import Dice


class Battle:
    def __init__(self, character, monster):
        self.character = character
        self.monster = monster
        self.round_count = 0

    def calculate_initiative(self):
        initiative = [
            (self.character.name, self.character.dexterity + Dice.roll_d20()),
            (self.monster.name, self.monster.dexterity + Dice.roll_d20())
        ]
        return sorted(initiative, key=lambda x: x[1], reverse=True)

    def player_turn(self):
        print(f"\n{self.character.name}'s turn!")
        while True:
            action = input("Do you want to (a)ttack, (d)efend, (u)se an item, or use a (s)pecial ability? ").lower()
            if action == 'a':
                return self.player_attack()
            elif action == 'd':
                return self.player_defend()
            elif action == 'u':
                return self.player_use_item()
            elif action == 's':
                return self.player_special_ability()
            else:
                print("Invalid action. Please choose 'a', 'd', 'u', or 's'.")

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
        if random.random() < 0.7:  # 70% chance to attack
            return self.monster_attack()
        elif random.random() < 0.9:  # 20% chance to defend
            return self.monster_defend()
        else:  # 10% chance to use special ability
            return self.monster_special_ability()

    def player_attack(self):
        attack_roll = self.character.strength + Dice.roll_d20()
        print(f"{self.character.name} rolls {attack_roll} to hit against AC {self.monster.armor_class}")

        if attack_roll >= self.monster.armor_class:
            damage_dealt = max(1, Dice.roll_d6() + self.character.strength)
            actual_damage = self.monster.take_damage(damage_dealt)
            print(f"{self.character.name} hit {self.monster.name} for {actual_damage} damage!")
        else:
            actual_damage = 0
            print(f"{self.character.name}'s attack missed!")
        return attack_roll, actual_damage

    def monster_attack(self):
        attack_roll = self.monster.strength + Dice.roll_d20()
        print(f"{self.monster.name} rolls {attack_roll} to hit against AC {self.character.armor_class}")

        if attack_roll >= self.character.armor_class:
            damage_dealt = max(1, Dice.roll_d6() + self.monster.strength)
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
        print(f"Battle begins: {self.character.name} vs {self.monster.name}")
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
            #self.monster.armor_class = self.monster.base_armor_class

    def end_battle(self, character_won):
        if character_won:
            xp_award = self.calculate_xp_award()
            self.character.gain_xp(xp_award)
            print(f"{self.character.name} has won the battle and gained {xp_award} experience points!")
            return "player"
        else:
            print(f"{self.monster.name} has defeated {self.character.name}!")
            return "monster"

    def calculate_xp_award(self):
        # Example: Award XP based on the monster's level and the number of rounds
        base_xp = 100 * self.monster.level
        round_bonus = max(0, 10 * (10 - self.round_count))  # Bonus for quick victories
        return base_xp + round_bonus