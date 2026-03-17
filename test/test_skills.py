"""Tests for the skills system — modifiers, proficiency, and skill checks."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dice import Dice
from characterFactory import CharacterFactory
from skills import SKILLS, calculate_skill_modifier, make_skill_check


class TestSkillModifier:
    def _make_char(self):
        factory = CharacterFactory()
        char = factory.create_character("Tester", "Human", "Fighter")
        char.add_skill_proficiency("Athletics")
        return char

    def test_proficient_skill_includes_bonus(self):
        char = self._make_char()
        mod = calculate_skill_modifier(char, "Athletics")
        expected = char.strength_modifier + char.proficiency_bonus
        assert mod == expected

    def test_non_proficient_skill_no_bonus(self):
        char = self._make_char()
        mod = calculate_skill_modifier(char, "Arcana")
        expected = char.intelligence_modifier  # no proficiency bonus
        assert mod == expected

    def test_all_skills_resolve_to_valid_ability(self):
        """Every skill in the SKILLS dict should map to a real ability modifier."""
        char = self._make_char()
        for skill_name in SKILLS:
            mod = calculate_skill_modifier(char, skill_name)
            assert isinstance(mod, int)

    def test_invalid_skill_raises(self):
        char = self._make_char()
        try:
            calculate_skill_modifier(char, "Nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestSkillCheck:
    def setup_method(self):
        self._orig_d20 = Dice.roll_d20

    def teardown_method(self):
        Dice.roll_d20 = self._orig_d20

    def _make_char(self):
        factory = CharacterFactory()
        char = factory.create_character("Tester", "Human", "Rogue")
        char.add_skill_proficiency("Stealth")
        return char

    def test_check_returns_required_fields(self):
        char = self._make_char()
        result = make_skill_check(char, "Stealth", 10)
        assert "skill" in result
        assert "roll" in result
        assert "modifier" in result
        assert "total" in result
        assert "dc" in result
        assert "success" in result

    def test_high_roll_succeeds(self):
        Dice.roll_d20 = lambda: 20
        char = self._make_char()
        result = make_skill_check(char, "Stealth", 15)
        assert result["success"] is True

    def test_low_roll_fails(self):
        Dice.roll_d20 = lambda: 1
        char = self._make_char()
        result = make_skill_check(char, "Stealth", 30)
        assert result["success"] is False

    def test_total_equals_roll_plus_modifier(self):
        Dice.roll_d20 = lambda: 10
        char = self._make_char()
        result = make_skill_check(char, "Stealth", 15)
        assert result["total"] == result["roll"] + result["modifier"]

    def test_exact_dc_succeeds(self):
        """Meeting the DC exactly is a success."""
        char = self._make_char()
        mod = calculate_skill_modifier(char, "Stealth")
        # Set roll so roll + mod == DC
        dc = 15
        Dice.roll_d20 = lambda: dc - mod
        result = make_skill_check(char, "Stealth", dc)
        assert result["success"] is True


class TestProficiencyScaling:
    def test_proficiency_bonus_at_level_1(self):
        factory = CharacterFactory()
        char = factory.create_character("Test", "Human", "Fighter")
        # Formula: 1 + (level // 4). At level 1: 1 + 0 = 1
        assert char.proficiency_bonus == 1

    def test_proficiency_increases_with_level(self):
        factory = CharacterFactory()
        char = factory.create_character("Test", "Human", "Fighter")
        char.level = 5
        char.update_proficiency_bonus()
        assert char.proficiency_bonus == 2  # 1 + 5//4 = 2

        char.level = 9
        char.update_proficiency_bonus()
        assert char.proficiency_bonus == 3  # 1 + 9//4 = 3
