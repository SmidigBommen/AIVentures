import unittest
from characterFactory import CharacterFactory
from monsterFactory import MonsterFactory
from battleAI import Battle
from dice import Dice
from equipmentType import EquipmentType


class BattleSmokeTest(unittest.TestCase):
    def setUp(self):
        self.character_factory = CharacterFactory()
        self.monster_factory = MonsterFactory()

        # Create test entities
        self.character = self.character_factory.create_character("Test Hero", "Human", "Fighter")
        self.monster = self.monster_factory.create_monster("Test Monster", "Goblin", "Ranger", 1)

        # Setup battle
        self.battle = Battle(self.character, self.monster)

    def test_initiative_calculation(self):
        initiative = self.battle.calculate_initiative()
        self.assertEqual(len(initiative), 2)
        self.assertIn(self.character.name, [entry[0] for entry in initiative])
        self.assertIn(self.monster.name, [entry[0] for entry in initiative])

    def test_attack_mechanics(self):
        # Mock dice rolls for consistent testing
        original_roll = Dice.roll_d20
        Dice.roll_d20 = lambda: 20  # Always hit

        # Test player attack
        attack_roll, damage = self.battle.player_attack()
        self.assertGreaterEqual(attack_roll, self.monster.armor_class)
        self.assertGreater(damage, 0)

        # Test monster attack
        attack_roll, damage = self.battle.monster_attack()
        self.assertGreaterEqual(attack_roll, self.character.armor_class)
        self.assertGreater(damage, 0)

        # Restore original dice function
        Dice.roll_d20 = original_roll

    def test_defense_mechanics(self):
        action, bonus = self.battle.player_defend()
        self.assertEqual(action, "defend")
        self.assertGreater(bonus, 0)

        action, bonus = self.battle.monster_defend()
        self.assertEqual(action, "defend")
        self.assertGreater(bonus, 0)

    def test_victory_detection(self):
        # Test no victory yet
        self.assertIsNone(self.battle.check_victory())

        # Test monster victory
        self.character.current_hit_points = 0
        self.assertEqual(self.battle.check_victory(), self.monster.name)

        # Test player victory
        self.character.current_hit_points = 10
        self.monster.current_hit_points = 0
        self.assertEqual(self.battle.check_victory(), self.character.name)


if __name__ == "__main__":
    unittest.main()