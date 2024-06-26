import json
from monster import Monster


class MonsterFactory:
    def __init__(self):
        with open("monster_default_values.json") as f:
            self.races = json.load(f)

    def create_monster(self, name, race, class_name):
        race_stats = self.races[race]

        m = Monster(name, race, class_name, race_stats["Strength"], race_stats["Dexterity"],
                              race_stats["Constitution"], race_stats["Intelligence"],
                              race_stats["Wisdom"], race_stats["Charisma"], 10, 2, 0)
        # name, race, class_name, strength, dexterity,
        # constitution, intelligence, wisdom, charisma, hit_points, armor_class, damage_reduction
        return m
