from random import random
from dice import Dice
class Battle_:
    def __init__(self, character, monster):
        self.character = character
        self.monster = monster

    def calculate_initiative(self):
        initiative = []
        initiative.append((self.character.name, self.character.dexterity + Dice.roll_d20()))
        initiative.append((self.monster.name, self.monster.dexterity + Dice.roll_d20()))
        initiative.sort(key=lambda x: x[1], reverse=True)
        return initiative

## turn from Claude AI
    def player_turn(self):
        print(f"\n{self.character.name}'s turn!")
        action = input("Do you want to (a)ttack or (d)efend? ").lower()
        if action == 'a':
            self.player_attack()
        elif action == 'd':
            self.player_defend()
        else:
            print("Invalid action. Defending by default.")
            self.player_defend()
## -----
    def monster_turn(self):
        print(f"\n{self.monster.name}'s turn!")
        if random.random() < 0.8:  # 80% chance to attack
            self.monster_attack()
        else:
            self.monster_defend()

    def player_attack(self):
        attack_roll = self.character.strength + Dice.roll_d20()
        if attack_roll >= self.monster.armor_class:
            damage_dealt = max(1, Dice.roll_d6() + self.character.strength - self.monster.damage_reduction)
            self.monster.hit_points -= damage_dealt
        else:
            damage_dealt = 0
        return attack_roll, damage_dealt

    def monster_attack(self):
        attack_roll = self.monster.strength + Dice.roll_d20()
        if attack_roll >= self.character.armor_class:
            damage_dealt = max(1, Dice.roll_d6() + self.monster.strength - self.character.damage_reduction)
            self.character.hit_points -= damage_dealt
        else:
            damage_dealt = 0
        return attack_roll, damage_dealt

    def check_victory(self):
        if self.character.hit_points <= 0:
            return "monster"
        elif self.monster.hit_points <= 0:
            return "player"
        else:
            return None

    def run_battle(self):
        initiative = self.calculate_initiative()
        while True:
            for name, _ in initiative:
                if name == self.character.name:
                    self.player_attack()
                else:
                    self.monster_attack()

                winner = self.check_victory()
                if winner is not None:
                    return winner

    def end_battle(self, character_won):
        if character_won:
            xp_award = self.calculate_xp_award()
            self.character.gain_xp(xp_award)
            print(f"{self.character.name} has won the battle and gained {xp_award} experience points!")
        else:
            print(f"{self.monster.name} has won the battle!")

    def calculate_xp_award(self):
        # Example: Award XP based on the monster's level
        return 100 * self.monster.level
