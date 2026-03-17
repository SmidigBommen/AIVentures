"""Level-up and XP calculations — used by both web and CLI."""


FULL_CASTERS = {"Wizard", "Sorcerer", "Warlock", "Cleric", "Druid", "Bard"}
HALF_CASTERS = {"Paladin", "Ranger"}


def calculate_max_pp(class_name, level, primary_modifier):
    """Calculate max power points for a class at a given level."""
    if class_name in FULL_CASTERS:
        pp = level + primary_modifier
    elif class_name in HALF_CASTERS:
        pp = (level // 2) + primary_modifier
    else:
        pp = (level // 3) + primary_modifier
    return max(2, pp)


def apply_level_up(character, roll_hp=False):
    """Apply a single level-up to a character. Returns result dict.

    This is a convenience wrapper around Character.level_up() for
    cases where the caller doesn't have direct access to the character method
    (e.g. web routes that work with serialized state).
    """
    return character.level_up(roll_hp=roll_hp)


def apply_xp(character, xp_amount, roll_hp=False):
    """Add XP and process any resulting level-ups. Returns list of level-up results."""
    return character.gain_xp(xp_amount, roll_hp=roll_hp)
