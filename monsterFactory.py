import json
from monster import Monster
from dice import Dice


class MonsterFactory:
    def __init__(self):
        with open("json/monster_default_values.json", encoding="utf-8") as f:
            self.races = json.load(f)

    def create_monster(self, name, race, class_name, monster_level, weapon_name):
        race_stats = self.races[race]

        m = Monster(name, race, class_name, race_stats["Strength"], (race_stats["Strength"] - 10) // 2,
                    race_stats["Dexterity"], (race_stats["Dexterity"] - 10) // 2, race_stats["Constitution"],
                    (race_stats["Constitution"] - 10) // 2, race_stats["Intelligence"],
                    (race_stats["Intelligence"] - 10) // 2, race_stats["Wisdom"], (race_stats["Wisdom"] - 10) // 2,
                    race_stats["Charisma"], (race_stats["Charisma"] - 10) // 2,
                    self._calculate_max_hp(race_stats, monster_level),
                    base_ac=race_stats["base_ac"], damage_reduction=0, monster_level=monster_level, weapon_name=weapon_name)
        return m

    @staticmethod
    def _calculate_max_hp(race_stats, monster_level):
        hit_die = race_stats["hit_die"]
        con_modifier = (race_stats["Constitution"] - 10) // 2
        hp = monster_level + Dice.roll(hit_die) + Dice.roll(hit_die) + con_modifier
        return max(1, hp)