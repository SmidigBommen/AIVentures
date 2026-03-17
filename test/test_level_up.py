"""Tests for Character.level_up() and gain_xp() — the refactored leveling system."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from characterFactory import CharacterFactory
from dice import Dice


class TestLevelUp:
    def _make_char(self, class_name="Fighter"):
        factory = CharacterFactory()
        return factory.create_character("Hero", "Human", class_name)

    def test_level_up_increments_level(self):
        char = self._make_char()
        char.xp = 150  # exactly at threshold
        result = char.level_up()
        assert char.level == 2
        assert result["new_level"] == 2

    def test_level_up_returns_hp_increase(self):
        char = self._make_char()
        char.xp = 150
        result = char.level_up()
        assert result["hp_increase"] >= 1
        assert "con_modifier" in result

    def test_level_up_average_hp(self):
        """Average HP = (hit_die // 2) + 1 + con_mod, min 1."""
        char = self._make_char("Fighter")  # d10
        old_max_hp = char.max_hit_points
        char.xp = 150
        result = char.level_up(roll_hp=False)
        expected_avg = (10 // 2) + 1 + char.get_constitution_modifier()
        expected = max(1, expected_avg)
        assert result["hp_increase"] == expected
        assert char.max_hit_points == old_max_hp + expected

    def test_level_up_rolled_hp(self):
        """Rolled HP uses actual die roll + con mod, min 1."""
        char = self._make_char("Wizard")  # d6
        orig_roll = Dice.roll
        Dice.roll = lambda size: 1  # minimum roll
        char.xp = 150
        result = char.level_up(roll_hp=True)
        Dice.roll = orig_roll
        con_mod = char.get_constitution_modifier()
        expected = max(1, 1 + con_mod)
        assert result["hp_increase"] == expected
        assert result["rolled"] is True

    def test_level_up_updates_proficiency(self):
        char = self._make_char()
        char.xp = 150
        for _ in range(4):
            char.level_up()
        # At level 5, proficiency should be updated
        assert char.proficiency_bonus == 1 + (char.level // 4)

    def test_level_up_updates_xp_to_next_level(self):
        char = self._make_char()
        char.xp = 150
        char.level_up()
        assert char.xp_to_next_level == char.level * 150


class TestGainXP:
    def _make_char(self):
        factory = CharacterFactory()
        return factory.create_character("Hero", "Human", "Fighter")

    def test_no_level_up(self):
        char = self._make_char()
        results = char.gain_xp(10)
        assert len(results) == 0
        assert char.level == 1
        assert char.xp == 10

    def test_single_level_up(self):
        char = self._make_char()
        results = char.gain_xp(150)
        assert len(results) == 1
        assert char.level == 2

    def test_multi_level_up(self):
        """Enough XP to gain multiple levels at once."""
        char = self._make_char()
        # Level 1->2 needs 150, level 2->3 needs 300, total = 450
        results = char.gain_xp(450)
        assert len(results) == 2
        assert char.level == 3

    def test_xp_remainder_preserved(self):
        char = self._make_char()
        char.gain_xp(200)
        # Needed 150 to level, so 50 leftover
        assert char.xp == 50
        assert char.level == 2

    def test_gain_xp_returns_hp_increases(self):
        char = self._make_char()
        results = char.gain_xp(450)
        total_hp = sum(r["hp_increase"] for r in results)
        assert total_hp >= 2  # at least 1 HP per level

    def test_zero_xp_no_change(self):
        char = self._make_char()
        results = char.gain_xp(0)
        assert len(results) == 0
        assert char.level == 1
