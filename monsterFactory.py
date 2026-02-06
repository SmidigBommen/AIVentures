import json
from monster import Monster
from dice import Dice


class MonsterFactory:
    def __init__(self):
        with open("json/monster_default_values.json") as f:
            self.races = json.load(f)

    def create_monster(self, name, race, class_name, monster_level, weapon_name):
        self.race_stats = self.races[race]

        m = Monster(name, race, class_name, self.race_stats["Strength"], (self.race_stats["Strength"] - 10) // 2,
                    self.race_stats["Dexterity"], (self.race_stats["Dexterity"] - 10) // 2, self.race_stats["Constitution"],
                    (self.race_stats["Constitution"] - 10) // 2, self.race_stats["Intelligence"],
                    (self.race_stats["Intelligence"] - 10) // 2, self.race_stats["Wisdom"], (self.race_stats["Wisdom"] - 10) // 2,
                    self.race_stats["Charisma"], (self.race_stats["Charisma"] - 10) // 2, self.calculate_max_hit_points(race, monster_level),
                    base_ac=self.race_stats["base_ac"], damage_reduction=0, monster_level=monster_level, weapon_name=weapon_name)
        return m

    def calculate_max_hit_points(self, monster_race, monster_level):
        hit_die = self.race_stats["hit_die"]
        con_modifier = (self.race_stats["Constitution"] - 10) // 2
        hp = monster_level + Dice.roll(hit_die) + Dice.roll(hit_die) + con_modifier
        return max(1, hp)