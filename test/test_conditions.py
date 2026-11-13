"""Tests for conditions: damage over time, regeneration and stun."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.effects import (
    is_stunned, resolve_round_conditions, describe_effect, tick_effects, get_effect_bonus,
)


def _eff(stat, value, duration=2):
    return {"stat": stat, "value": value, "duration": duration, "source": "test"}


def test_dots_stack_and_report_sources():
    result = resolve_round_conditions([_eff("poison", 3), _eff("burn", 2), _eff("bleed", 1)])
    assert result["damage"] == 6
    assert result["heal"] == 0
    assert ("poison", 3) in result["sources"]


def test_regen_heals():
    result = resolve_round_conditions([_eff("regen", 4)])
    assert result == {"damage": 0, "heal": 4, "sources": [("regen", 4)]}


def test_stat_modifiers_are_not_conditions():
    result = resolve_round_conditions([_eff("ac", -2), _eff("damage_bonus", 5)])
    assert result["damage"] == 0 and result["heal"] == 0


def test_conditions_do_not_leak_into_stat_bonuses():
    effects = [_eff("poison", 3), _eff("ac", 2)]
    assert get_effect_bonus(effects, "ac") == 2
    assert get_effect_bonus(effects, "damage_bonus") == 0


def test_stun_detection_and_expiry():
    effects = [_eff("stun", 1, duration=1)]
    assert is_stunned(effects)
    assert not is_stunned(tick_effects(effects))


def test_describe_effect():
    assert describe_effect(_eff("poison", 3)) == "Poisoned (3 damage/round)"
    assert describe_effect(_eff("stun", 1)) == "Stunned"
    assert describe_effect(_eff("attack_bonus", -2)) == "attack bonus -2"
