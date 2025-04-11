import json
from armor import Armor

class ArmorFactory:
    def __init__(self):
        with open("armor_catalog.json") as f:
            self.armor_catalog = json.load(f)

        # Combine all armors into a single dictionary for easy access
        self.all_armors = {}
        for category, armors in self.armor_catalog.items():
            for armor_name, armor_data in armors.items():
                self.all_armors[armor_name] = armor_data
                # Add the armor type (light_armor, medium_armor, etc.) to the data
                self.all_armors[armor_name]["type"] = category

    def get_armor_list(self):
        """Returns a list of all armor names."""
        return list(self.all_armors.keys())
    
    def get_armor_by_name(self, armor_name):
        """Creates and returns an Armor object based on the armor name."""
        if armor_name not in self.all_armors:
            raise ValueError(f"Armor {armor_name} not found in the catalog")

        armor_data = self.all_armors[armor_name]
        
        return Armor(
            name=armor_name,
            base_ac=armor_data["base_ac"],
            category=armor_data["category"]
        )