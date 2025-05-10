import json
from weapon import Weapon


class WeaponFactory:
    def __init__(self):
        with open("json/weapon-catalog.json") as f:
            self.weapon_catalog = json.load(f)

        # Combine all weapons into a single dictionary for easy access
        self.all_weapons = {}
        for category, weapons in self.weapon_catalog.items():
            for weapon_name, weapon_data in weapons.items():
                self.all_weapons[weapon_name] = weapon_data
                # Add the weapon type (simple_melee, martial_ranged, etc.) to the data
                self.all_weapons[weapon_name]["type"] = category

    def get_weapon_list(self):
        """Returns a list of all weapon names."""
        return list(self.all_weapons.keys())

    def get_weapons_by_category(self, category=None):
        """Returns a dictionary of weapons filtered by category (simple/martial) if provided."""
        if category is None:
            return self.all_weapons

        return {name: data for name, data in self.all_weapons.items()
                if data["category"].lower() == category.lower()}

    def get_weapons_by_type(self, weapon_type=None):
        """Returns a dictionary of weapons filtered by type (melee/ranged) if provided."""
        if weapon_type is None:
            return self.all_weapons

        return {name: data for name, data in self.all_weapons.items()
                if weapon_type.lower() in data["type"].lower()}

    def get_weapon_by_name(self, weapon_name):
        """Creates and returns a Weapon object based on the weapon name."""
        if weapon_name not in self.all_weapons:
            raise ValueError(f"Weapon {weapon_name} not found in the catalog")

        weapon_data = self.all_weapons[weapon_name]
        properties = weapon_data.get("properties", [])
        damage_dice_count = weapon_data.get("damage_dice_count", 1)
        description = weapon_data.get("description", "")

        return Weapon(
            name=weapon_name,
            description=description,
            damage_die=weapon_data["damage_die"],
            damage_type=weapon_data["damage_type"],
            category=weapon_data["category"],
            properties=properties,
            damage_dice_count=damage_dice_count
        )