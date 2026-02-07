import random

from dice import Dice
from items import HealingPotion
from weaponFactory import WeaponFactory
from armorFactory import ArmorFactory


class LootGenerator:
    # Loot type weights
    LOOT_WEIGHTS = {
        "potion": 40,
        "gold": 25,
        "weapon": 20,
        "armor": 15,
    }

    # Tier definitions based on monster level
    TIERS = {
        "low": {"min_level": 1, "max_level": 3},
        "mid": {"min_level": 4, "max_level": 7},
        "high": {"min_level": 8, "max_level": 11},
        "elite": {"min_level": 12, "max_level": 999},
    }

    # Potion definitions per tier
    POTIONS = {
        "low": ("Small Healing Potion", 10),
        "mid": ("Healing Potion", 20),
        "high": ("Greater Healing Potion", 35),
        "elite": ("Superior Healing Potion", 50),
    }

    # Weapon types available per tier (keys into weapon catalog categories)
    WEAPON_TYPES = {
        "low": ["simple_melee"],
        "mid": ["simple_melee", "simple_ranged"],
        "high": ["martial_melee", "martial_ranged"],
        "elite": ["martial_melee", "martial_ranged"],
    }

    # Armor types available per tier (keys into armor catalog categories)
    ARMOR_TYPES = {
        "low": ["light_armor"],
        "mid": ["light_armor", "medium_armor"],
        "high": ["medium_armor", "heavy_armor"],
        "elite": ["heavy_armor"],
    }

    def __init__(self):
        self.weapon_factory = WeaponFactory()
        self.armor_factory = ArmorFactory()

    @staticmethod
    def _get_tier(monster_level):
        if monster_level <= 3:
            return "low"
        elif monster_level <= 7:
            return "mid"
        elif monster_level <= 11:
            return "high"
        else:
            return "elite"

    @staticmethod
    def calculate_drop_chance(monster_level, player_level):
        return min(1.0, 0.20 + max(0, monster_level - player_level) * 0.15)

    def determine_loot_type(self):
        types = list(self.LOOT_WEIGHTS.keys())
        weights = list(self.LOOT_WEIGHTS.values())
        return random.choices(types, weights=weights, k=1)[0]

    def generate_loot(self, monster_level, player_level):
        drop_chance = self.calculate_drop_chance(monster_level, player_level)
        if random.random() >= drop_chance:
            return None

        tier = self._get_tier(monster_level)
        loot_type = self.determine_loot_type()

        generators = {
            "potion": self._generate_potion,
            "gold": self._generate_gold,
            "weapon": self._generate_weapon,
            "armor": self._generate_armor,
        }
        return generators[loot_type](tier)

    def _generate_potion(self, tier):
        name, healing = self.POTIONS[tier]
        potion = HealingPotion(name, healing)
        return {
            "type": "potion",
            "item": potion,
            "message": f"{name} (heals {healing} HP)",
        }

    def _generate_gold(self, tier):
        if tier == "low":
            amount = 5 + Dice.roll_d6()
        elif tier == "mid":
            amount = 10 + Dice.roll_d10()
        elif tier == "high":
            amount = 20 + Dice.roll_d12()
        else:  # elite
            amount = 40 + Dice.roll_d12() + Dice.roll_d12()
        return {
            "type": "gold",
            "amount": amount,
            "message": f"{amount} bonus gold",
        }

    def _generate_weapon(self, tier):
        allowed_types = self.WEAPON_TYPES[tier]
        chosen_type = random.choice(allowed_types)
        weapons_in_category = self.weapon_factory.get_weapons_by_type(chosen_type)
        weapon_name = random.choice(list(weapons_in_category.keys()))
        weapon = self.weapon_factory.get_weapon_by_name(weapon_name)
        return {
            "type": "weapon",
            "item": weapon,
            "message": f"{weapon_name} (weapon)",
        }

    def _generate_armor(self, tier):
        allowed_types = self.ARMOR_TYPES[tier]
        chosen_type = random.choice(allowed_types)
        # Filter armors by the chosen category type
        armors_in_category = {
            name: data
            for name, data in self.armor_factory.all_armors.items()
            if data["type"] == chosen_type
        }
        armor_name = random.choice(list(armors_in_category.keys()))
        armor = self.armor_factory.get_armor_by_name(armor_name)
        return {
            "type": "armor",
            "item": armor,
            "message": f"{armor_name} (armor)",
        }
