"""Tests for engine.effects — buff/debuff duration, stacking, and expiry."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.effects import get_effect_bonus, tick_effects, apply_effect, clear_effects


class TestGetEffectBonus:
    def test_empty_effects(self):
        assert get_effect_bonus([], "attack_bonus") == 0

    def test_single_effect(self):
        effects = [{"stat": "attack_bonus", "value": 2, "duration": 3, "source": "spell"}]
        assert get_effect_bonus(effects, "attack_bonus") == 2

    def test_stacking_effects(self):
        effects = [
            {"stat": "attack_bonus", "value": 2, "duration": 3, "source": "spell_a"},
            {"stat": "attack_bonus", "value": 3, "duration": 1, "source": "spell_b"},
        ]
        assert get_effect_bonus(effects, "attack_bonus") == 5

    def test_different_stats_dont_stack(self):
        effects = [
            {"stat": "attack_bonus", "value": 2, "duration": 3, "source": "spell"},
            {"stat": "damage_bonus", "value": 5, "duration": 3, "source": "spell"},
        ]
        assert get_effect_bonus(effects, "attack_bonus") == 2
        assert get_effect_bonus(effects, "damage_bonus") == 5

    def test_negative_values(self):
        effects = [{"stat": "ac", "value": -2, "duration": 1, "source": "curse"}]
        assert get_effect_bonus(effects, "ac") == -2

    def test_mixed_positive_negative(self):
        effects = [
            {"stat": "ac", "value": 3, "duration": 0, "source": "shield"},
            {"stat": "ac", "value": -1, "duration": 2, "source": "curse"},
        ]
        assert get_effect_bonus(effects, "ac") == 2

    def test_nonexistent_stat_returns_zero(self):
        effects = [{"stat": "attack_bonus", "value": 2, "duration": 3, "source": "spell"}]
        assert get_effect_bonus(effects, "nonexistent") == 0


class TestTickEffects:
    def test_empty_list(self):
        assert tick_effects([]) == []

    def test_permanent_effect_persists(self):
        """Duration 0 = lasts entire combat."""
        effects = [{"stat": "ac", "value": 2, "duration": 0, "source": "aura"}]
        result = tick_effects(effects)
        assert len(result) == 1
        assert result[0]["duration"] == 0

    def test_duration_1_expires(self):
        effects = [{"stat": "ac", "value": 2, "duration": 1, "source": "spell"}]
        result = tick_effects(effects)
        assert len(result) == 0

    def test_duration_2_decrements(self):
        effects = [{"stat": "ac", "value": 2, "duration": 2, "source": "spell"}]
        result = tick_effects(effects)
        assert len(result) == 1
        assert result[0]["duration"] == 1

    def test_multi_tick_lifecycle(self):
        """Track an effect through creation to expiry."""
        effects = [{"stat": "ac", "value": 2, "duration": 3, "source": "spell"}]
        effects = tick_effects(effects)  # 3 -> 2
        assert len(effects) == 1 and effects[0]["duration"] == 2
        effects = tick_effects(effects)  # 2 -> 1
        assert len(effects) == 1 and effects[0]["duration"] == 1
        effects = tick_effects(effects)  # 1 -> removed
        assert len(effects) == 0

    def test_mixed_durations(self):
        effects = [
            {"stat": "ac", "value": 2, "duration": 0, "source": "permanent"},
            {"stat": "attack_bonus", "value": 1, "duration": 1, "source": "expiring"},
            {"stat": "damage_bonus", "value": 3, "duration": 5, "source": "long"},
        ]
        result = tick_effects(effects)
        assert len(result) == 2
        stats = {e["source"] for e in result}
        assert "permanent" in stats
        assert "long" in stats
        assert "expiring" not in stats

    def test_tick_does_not_mutate_original(self):
        effects = [{"stat": "ac", "value": 2, "duration": 3, "source": "spell"}]
        result = tick_effects(effects)
        assert effects[0]["duration"] == 3  # original unchanged
        assert result[0]["duration"] == 2


class TestApplyEffect:
    def test_adds_effect(self):
        effects = []
        apply_effect(effects, "ac", 2, 3, "Shield of Faith")
        assert len(effects) == 1
        assert effects[0] == {"stat": "ac", "value": 2, "duration": 3, "source": "Shield of Faith"}

    def test_stacks_on_existing(self):
        effects = [{"stat": "ac", "value": 1, "duration": 0, "source": "aura"}]
        apply_effect(effects, "ac", 2, 3, "spell")
        assert len(effects) == 2


class TestClearEffects:
    def test_returns_empty(self):
        assert clear_effects() == []
        assert clear_effects([{"stat": "ac", "value": 1, "duration": 0, "source": "x"}]) == []
