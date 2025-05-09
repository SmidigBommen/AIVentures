import json
from characterFactory import CharacterFactory
from weaponFactory import WeaponFactory


class CharacterCreator:
    def __init__(self):
        self.character_factory = CharacterFactory()
        self.weapon_factory = WeaponFactory()

        with open("races.json") as jsonfile:
            self.races = json.load(jsonfile)

        with open("classes_properties.json") as jsonfile:
            self.classes_properties = json.load(jsonfile)

    def create_character(self):
        name = self.get_character_name()
        race = self.choose_race()
        class_name = self.choose_class()

        # Proficiencies
        character = self.character_factory.create_character(name, race, class_name)
        chosen_skills = self.choose_skill_proficiencies(class_name)
        for skill in chosen_skills:
            character.add_skill_proficiency(skill)

        if class_name in self.classes_properties:
            for ability in self.classes_properties[class_name]["saving_throw_proficiencies"]:
                character.add_saving_throw_proficiency(ability)

        # Weapon
        weapon = self.choose_weapon()
        character.add_item(weapon)
        character.equip_weapon(weapon)

        return character

    def get_character_name(self):
        while True:
            name = input("Enter your character's name: ").strip()
            if name:
                return name
            print("Name cannot be empty. Please try again.")

    def choose_race(self):
        print("\nAvailable races:")
        for i, race in enumerate(self.races.keys(), 1):
            print(f"{i}. {race}")

        while True:
            choice = input("Choose a race (enter the number): ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(self.races):
                    return list(self.races.keys())[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def choose_class(self):
        print("\nAvailable classes:")

        # Get the class names from the classes_properties dictionary keys
        class_names = list(self.classes_properties.keys())

        # Display classes with their hit die information
        for i, class_name in enumerate(class_names, 1):
            hit_die = self.classes_properties[class_name].get("hit_die", 8)
            print(f"{i}. {class_name} (Hit Die: d{hit_die})")

        while True:
            choice = input("Choose a class (enter the number): ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(class_names):
                    return class_names[index]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")


    def choose_weapon(self):
        print("\nAvailable weapons:")
        weapons = self.weapon_factory.get_weapon_list()

        for i, weapon in enumerate(weapons, 1):
            print(f"{i}. {weapon}")

        while True:
            choice = input("Choose a weapon (enter the number): ")
            try:
                index = int(choice) - 1
                if 0 <= index < len(weapons):
                    return self.weapon_factory.get_weapon_by_name(weapons[index])
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def get_all_skills(self):
        """Get list of all skills from the skills module."""
        from skills import SKILLS
        return SKILLS.keys()

    def choose_skill_proficiencies(self, class_name):
        """Let the player choose skill proficiencies based on their class."""

        # Get skill proficiency choices from classes_properties.json
        if class_name in self.classes_properties:
            class_data = self.classes_properties[class_name]
            available_skills = class_data.get("skill_proficiency_choices", [])
            num_to_choose = class_data.get("num_skill_choices", 2)
        else:
            # Fallback for classes not in the config
            available_skills = list(self.get_all_skills())[:4]  # Just use first 4 skills as default
            num_to_choose = 2
            print(f"Warning: Class '{class_name}' not found in configuration. Using default skills.")

        print(f"\nChoose {num_to_choose} skill proficiencies:")
        for i, skill in enumerate(available_skills, 1):
            print(f"{i}. {skill}")

        chosen_skills = []
        while len(chosen_skills) < num_to_choose:
            try:
                choice = input(f"Select skill #{len(chosen_skills) + 1} (1-{len(available_skills)}): ")
                if choice.lower() == 'q':
                    break

                index = int(choice) - 1
                if 0 <= index < len(available_skills):
                    skill = available_skills[index]
                    if skill not in chosen_skills:
                        chosen_skills.append(skill)
                    else:
                        print("You've already selected that skill. Choose another.")
                else:
                    print(f"Please enter a number between 1 and {len(available_skills)}.")
            except ValueError:
                print("Please enter a valid number.")

        return chosen_skills