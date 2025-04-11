import json
from monster import Monster


class MonsterFactory:
    def __init__(self):
        with open("monster_default_values.json") as f:
            self.races = json.load(f)

    def create_monster(self, name, race, class_name, monster_level):
        race_stats = self.races[race]

        m = Monster(name, race, class_name,
                   race_stats["Strength"],
                   (race_stats["Strength"] - 10) // 2,
                   race_stats["Dexterity"],
                   (race_stats["Dexterity"] - 10) // 2,
                   race_stats["Constitution"],
                   (race_stats["Constitution"] - 10) // 2,
                   race_stats["Intelligence"],
                   (race_stats["Intelligence"] - 10) // 2,
                   race_stats["Wisdom"],
                   (race_stats["Wisdom"] - 10) // 2,
                   race_stats["Charisma"],
                   (race_stats["Charisma"] - 10) // 2,
                   hit_points=10,
                   base_ac=race_stats["base_ac"],
                   damage_reduction=0,
                   monster_level=monster_level)
        return m
