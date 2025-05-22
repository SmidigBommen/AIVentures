import unittest

from character import WeaponSlot
from characterFactory import CharacterFactory
from weaponFactory import WeaponFactory


class CharacterCreationSmokeTest(unittest.TestCase):
    def setUp(self):
        self.character_factory = CharacterFactory()
        self.weapon_factory = WeaponFactory()

    def test_character_creation(self):
        # Test creating characters of different races and classes
        human_fighter = self.character_factory.create_character("Human Fighter", "Human", "Fighter")
        elf_wizard = self.character_factory.create_character("Elf Wizard", "Elf", "Wizard")
        dwarf_cleric = self.character_factory.create_character("Dwarf Cleric", "Dwarf", "Cleric")

        # Verify race bonuses were applied correctly
        self.assertEqual(human_fighter.strength_score, 11)  # Human gets +1 to all stats
        self.assertEqual(elf_wizard.dexterity_score, 12)  # Elf gets +2 to dexterity
        self.assertEqual(dwarf_cleric.constitution_score, 12)  # Dwarf gets +2 to constitution

        # Verify hit point calculation
        self.assertEqual(human_fighter.hit_die, 10)  # Fighter uses d10
        self.assertEqual(elf_wizard.hit_die, 6)  # Wizard uses d6
        self.assertEqual(dwarf_cleric.hit_die, 8)  # Cleric uses d8

        # Test equipping weapons
        longsword = self.weapon_factory.get_weapon_by_name("Longsword")
        human_fighter.add_item(longsword)
        human_fighter.equip_weapon(longsword)

        self.assertEqual(human_fighter.weapon_slots[WeaponSlot.MAIN_HAND], longsword)

        print("Character creation smoke test passed!")

if __name__ == '__main__':
    unittest.main()
