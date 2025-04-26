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

        character = self.character_factory.create_character(name, race, class_name)
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

##def main():
##    creator = CharacterCreator()
##    character = creator.create_character()
##    print("\nCharacter created successfully!")
##    print(character.get_stats())


##if __name__ == "__main__":
##    main()