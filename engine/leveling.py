"""Level-up and XP calculations — used by both web and CLI."""


FULL_CASTERS = {"Wizard", "Sorcerer", "Warlock", "Cleric", "Druid", "Bard"}
HALF_CASTERS = {"Paladin", "Ranger", "Monk"}   # Monk: ki pool


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


def grant_xp(character, xp, primary_modifier):
    """Award XP and handle everything a level-up entails.

    On level-up the character gains the new HP immediately and their power
    points are recalculated and refilled.

    Returns:
        dict with keys: xp, leveled_up (bool), new_level, hp_increase, level_ups (list)
    """
    old_level = character.level
    level_ups = character.gain_xp(xp)
    hp_increase = sum(lu["hp_increase"] for lu in level_ups)
    character.current_hit_points = min(
        character.max_hit_points, character.current_hit_points + hp_increase)

    leveled_up = character.level > old_level
    if leveled_up:
        character.max_power_points = calculate_max_pp(
            character.class_name, character.level, primary_modifier)
        character.power_points = character.max_power_points

    return {
        "xp": xp,
        "leveled_up": leveled_up,
        "new_level": character.level,
        "hp_increase": hp_increase,
        "level_ups": level_ups,
    }


# --- Ability Score Improvements -------------------------------------------

ABILITIES = ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma")
ASI_LEVELS = (4, 8, 12, 16, 19)
ASI_POINTS_PER_LEVEL = 2
ABILITY_SCORE_CAP = 20


def asi_points_earned(level):
    """Total improvement points a character of this level has ever been granted."""
    return ASI_POINTS_PER_LEVEL * sum(1 for asi_level in ASI_LEVELS if level >= asi_level)


def asi_points_available(character):
    """Improvement points the character has earned but not yet spent."""
    spent = sum(getattr(character, "ability_increases", {}).values())
    return max(0, asi_points_earned(character.level) - spent)


def apply_ability_increases(character, increases):
    """Add stored improvement points to a freshly built character's scores.

    Only touches scores, modifiers and AC. Hit points are stored separately and
    were already adjusted when the points were spent (see improve_ability).
    """
    character.ability_increases = {}
    for ability, points in (increases or {}).items():
        if ability not in ABILITIES or points <= 0:
            continue
        score = getattr(character, f"{ability}_score") + points
        setattr(character, f"{ability}_score", score)
        setattr(character, f"{ability}_modifier", (score - 10) // 2)
        character.ability_increases[ability] = points
    character.update_ac()


def improve_ability(character, ability, primary_ability):
    """Spend one improvement point on an ability score (+1).

    A higher Constitution modifier grants its HP retroactively for every level,
    Dexterity updates AC, and the class's primary ability refreshes the power
    point pool (the newly gained points are available immediately).

    Returns:
        dict with keys: ability, new_score, new_modifier, modifier_increased,
        hp_increase, pp_increase, points_left — or None if the point can't be spent.
    """
    ability = ability.lower()
    if ability not in ABILITIES or asi_points_available(character) <= 0:
        return None
    old_score = getattr(character, f"{ability}_score")
    if old_score >= ABILITY_SCORE_CAP:
        return None

    old_modifier = getattr(character, f"{ability}_modifier")
    new_score = old_score + 1
    new_modifier = (new_score - 10) // 2
    setattr(character, f"{ability}_score", new_score)
    setattr(character, f"{ability}_modifier", new_modifier)
    character.ability_increases[ability] = character.ability_increases.get(ability, 0) + 1

    hp_increase = 0
    if ability == "constitution" and new_modifier > old_modifier:
        hp_increase = (new_modifier - old_modifier) * character.level
        character.max_hit_points += hp_increase
        character.current_hit_points += hp_increase

    character.update_ac()

    old_max_pp = character.max_power_points
    primary_modifier = getattr(character, f"{primary_ability.lower()}_modifier", 0)
    character.max_power_points = calculate_max_pp(
        character.class_name, character.level, primary_modifier)
    pp_increase = max(0, character.max_power_points - old_max_pp)
    character.power_points = min(character.max_power_points, character.power_points + pp_increase)

    return {
        "ability": ability,
        "new_score": new_score,
        "new_modifier": new_modifier,
        "modifier_increased": new_modifier > old_modifier,
        "hp_increase": hp_increase,
        "pp_increase": pp_increase,
        "points_left": asi_points_available(character),
    }
