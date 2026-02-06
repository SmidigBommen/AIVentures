import unittest

from characterFactory import CharacterFactory
from armorFactory import ArmorFactory
from armor import Armor
from equipmentType import EquipmentType


class TestArmorAC(unittest.TestCase):
    def setUp(self):
        self.factory = CharacterFactory()
        self.armor_factory = ArmorFactory()
        # Human Fighter: base_ac=10, all stats 11, modifiers +0
        self.character = self.factory.create_character("Test Fighter", "Human", "Fighter")

    def test_unarmored_ac(self):
        """Unarmored AC = base_ac + dex_modifier."""
        expected = self.character.base_ac + self.character.dexterity_modifier
        self.assertEqual(self.character.armor_class, expected)

    def test_light_armor_ac(self):
        """Light armor AC = armor.base_ac + dex_modifier."""
        leather = self.armor_factory.get_armor_by_name("Leather")  # base_ac=11
        self.character.equip(leather)
        expected = 11 + self.character.dexterity_modifier
        self.assertEqual(self.character.armor_class, expected)

    def test_medium_armor_ac(self):
        """Medium armor AC = armor.base_ac + min(dex_modifier, 2)."""
        # Give character high DEX to verify the cap
        self.character.dexterity_modifier = 3
        chain_shirt = self.armor_factory.get_armor_by_name("Chain Shirt")  # base_ac=13
        self.character.equip(chain_shirt)
        expected = 13 + min(3, 2)  # 15
        self.assertEqual(self.character.armor_class, expected)

    def test_heavy_armor_ac(self):
        """Heavy armor AC = armor.base_ac (no DEX)."""
        self.character.dexterity_modifier = 3
        chain_mail = self.armor_factory.get_armor_by_name("Chain Mail")  # base_ac=16
        self.character.equip(chain_mail)
        self.assertEqual(self.character.armor_class, 16)

    def test_unequip_restores_unarmored_ac(self):
        """Unequipping armor restores unarmored AC."""
        original_ac = self.character.armor_class
        leather = self.armor_factory.get_armor_by_name("Leather")
        self.character.equip(leather)
        self.assertNotEqual(self.character.armor_class, original_ac)
        self.character.unequip(EquipmentType.ARMOR)
        self.assertEqual(self.character.armor_class, original_ac)

    def test_swap_armor_updates_ac(self):
        """Swapping armor correctly updates AC."""
        leather = self.armor_factory.get_armor_by_name("Leather")  # base_ac=11
        studded = self.armor_factory.get_armor_by_name("Studded Leather")  # base_ac=12
        self.character.equip(leather)
        ac_with_leather = self.character.armor_class
        self.character.equip(studded)
        ac_with_studded = self.character.armor_class
        self.assertNotEqual(ac_with_leather, ac_with_studded)
        expected = 12 + self.character.dexterity_modifier
        self.assertEqual(ac_with_studded, expected)

    def test_armor_factory_creates_correct_objects(self):
        """ArmorFactory creates Armor objects with correct attributes."""
        chain_mail = self.armor_factory.get_armor_by_name("Chain Mail")
        self.assertIsInstance(chain_mail, Armor)
        self.assertEqual(chain_mail.name, "Chain Mail")
        self.assertEqual(chain_mail.base_ac, 16)
        self.assertEqual(chain_mail.category, "Heavy")
        self.assertEqual(chain_mail.equipment_type, EquipmentType.ARMOR)


if __name__ == "__main__":
    unittest.main()
