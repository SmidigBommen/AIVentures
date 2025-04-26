
ABILITY_SCORES = [
    "STRENGTH",
    "DEXTERITY",
    "CONSTITUTION",
    "INTELLIGENCE",
    "WISDOM",
    "CHARISMA"
]

SKILLS = {
    # Strength-based skills
    "Athletics": "STRENGTH",
    
    # Dexterity-based skills
    "Acrobatics": "DEXTERITY",
    "Sleight of Hand": "DEXTERITY",
    "Stealth": "DEXTERITY",
    
    # Intelligence-based skills
    "Arcana": "INTELLIGENCE",
    "History": "INTELLIGENCE",
    "Investigation": "INTELLIGENCE",
    "Nature": "INTELLIGENCE",
    "Religion": "INTELLIGENCE",
    
    # Wisdom-based skills
    "Animal Handling": "WISDOM",
    "Insight": "WISDOM",
    "Medicine": "WISDOM",
    "Perception": "WISDOM",
    "Survival": "WISDOM",
    
    # Charisma-based skills
    "Deception": "CHARISMA",
    "Intimidation": "CHARISMA",
    "Performance": "CHARISMA",
    "Persuasion": "CHARISMA"
}

SAVING_THROWS = ABILITY_SCORES

def get_ability_for_skill(skill_name):
    return SKILLS.get(skill_name)

def get_skills_for_ability(ability):
    return [skill for skill, skill_ability in SKILLS.items() if skill_ability == ability]

def calculate_skill_modifier(character, skill_name):
    ability = get_ability_for_skill(skill_name)
    if not ability:
        raise ValueError(f"Unknown skill: {skill_name}")
    

    ability_modifier = getattr(character, f"{ability.lower()}_modifier")
    
    proficiency_bonus = 0
    if hasattr(character, 'skill_proficiencies') and skill_name in character.skill_proficiencies:
        proficiency_bonus = character.proficiency_bonus
    
    return ability_modifier + proficiency_bonus

def make_skill_check(character, skill_name, difficulty_class=10):

    from dice import Dice
    
    modifier = calculate_skill_modifier(character, skill_name)
    roll = Dice.roll_d20()
    total = roll + modifier
    
    success = total >= difficulty_class
    return {
        "skill": skill_name,
        "roll": roll,
        "modifier": modifier,
        "total": total,
        "dc": difficulty_class,
        "success": success
    }
