import json
from character import Character
from dice import Dice


class CharacterFactory:
    def __init__(self):
        with open("races.json") as f:
            self.races = json.load(f)

        with open("races_default_values.json") as default_values_file:
            self.races_defaults = json.load(default_values_file)

        with open("classes_properties.json") as classes_file:
            self.classes_properties = json.load(classes_file)

    def create_character(self, name, race, class_name):
        race_stats = self.races[race]
        race_default_values = self.races_defaults[race]

        # Get class hit die (or default to 8 if not found)
        hit_die = self.classes_properties.get(class_name, {}).get("hit_die", 8)

        # Set base attributes
        strength_score = race_default_values["strength"] + race_stats["strength_bonus"]
        dexterity_score = race_default_values["dexterity"] + race_stats["dexterity_bonus"]
        constitution_score = race_default_values["constitution"] + race_stats["constitution_bonus"]
        intelligence_score = race_default_values["intelligence"] + race_stats["intelligence_bonus"]
        wisdom_score = race_default_values["wisdom"] + race_stats["wisdom_bonus"]
        charisma_score = race_default_values["charisma"] + race_stats["charisma_bonus"]

        # Create character
        character = Character(
            name=name,
            race=race,
            class_name=class_name,
            strength_score= strength_score,
            strength_modifier= (strength_score - 10) // 2,
            dexterity_score=dexterity_score,
            dexterity_modifier= (dexterity_score - 10) // 2,
            constitution_score=constitution_score,
            constitution_modifier= (constitution_score - 10) // 2,
            intelligence_score=intelligence_score,
            intelligence_modifier= (intelligence_score - 10) // 2,
            wisdom_score=wisdom_score,
            wisdom_modifier= (wisdom_score- 10) // 2,
            charisma_score=charisma_score,
            charisma_modifier= (charisma_score - 10) // 2,

            hit_points=0,  # Will be calculated in initialize_hit_points
            base_ac=race_default_values["base_ac"],
            damage_reduction=0
        )

        # Initialize hit points based on class hit die and constitution modifier
        self.initialize_hit_points(character, hit_die)

        return character

    def initialize_hit_points(self, character, hit_die):
        # Calculate constitution modifier
        con_modifier = (character.constitution - 10) // 2

        # First level characters get maximum hit die value + con modifier
        max_hit_die_value = hit_die
        initial_hit_points = max_hit_die_value + con_modifier

        # Ensure minimum of 1 hit point
        initial_hit_points = max(1, initial_hit_points)

        # Set hit points
        character.max_hit_points = initial_hit_points
        character.current_hit_points = initial_hit_points

        # Store the hit die for future level ups
        character.hit_die = hit_die