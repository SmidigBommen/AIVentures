"""
Test script to verify that skills functionality is working correctly.
Run this script directly to test your skills implementation.
"""
import sys
from dice import Dice

def test_skills():
    """Test the skills implementation with a character."""
    # Import necessary classes
    try:
        from characterFactory import CharacterFactory
        from skills import SKILLS, calculate_skill_modifier, make_skill_check
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        sys.exit(1)
    
    print("\n=== TESTING SKILLS SYSTEM ===\n")
    
    # Create a test character
    print("Creating test character...")
    factory = CharacterFactory()
    character = factory.create_character("Tester", "Human", "Fighter")
    
    # Display character's base stats
    print(f"\nCharacter: {character.name}, Level {character.level}")
    print(f"Strength: {character.strength_score} (Modifier: {character.strength_modifier})")
    print(f"Dexterity: {character.dexterity_score} (Modifier: {character.dexterity_modifier})")
    print(f"Constitution: {character.constitution_score} (Modifier: {character.constitution_modifier})")
    print(f"Intelligence: {character.intelligence_score} (Modifier: {character.intelligence_modifier})")
    print(f"Wisdom: {character.wisdom_score} (Modifier: {character.wisdom_modifier})")
    print(f"Charisma: {character.charisma_score} (Modifier: {character.charisma_modifier})")
    print(f"Proficiency Bonus: +{character.proficiency_bonus}")
    
    # Add some skill proficiencies
    print("\nAdding skill proficiencies...")
    character.add_skill_proficiency("Athletics")
    character.add_skill_proficiency("Intimidation")
    character.add_skill_proficiency("Perception")
    
    # Set dice to always return 10 for testing predictability
    original_roll = Dice.roll_d20
    Dice.roll_d20 = lambda: 10
    
    # Test and display all skills
    print("\nTesting all skills:")
    print(f"{'Skill Name':<20} {'Ability':<15} {'Proficient':<12} {'Modifier':<10} {'Check Result (DC 15)'}")
    print("-" * 75)
    
    for skill_name, ability in SKILLS.items():
        # Check if character is proficient
        is_proficient = skill_name in character.skill_proficiencies
        proficient_str = "Yes" if is_proficient else "No"
        
        # Calculate modifier
        modifier = calculate_skill_modifier(character, skill_name)
        
        # Make a skill check against DC 15
        check_result = make_skill_check(character, skill_name, 15)
        success_str = "Success" if check_result["success"] else "Failure"
        result_str = f"{check_result['total']} ({success_str})"
        
        print(f"{skill_name:<20} {ability:<15} {proficient_str:<12} {modifier:<+10} {result_str}")
    
    # Test level up and proficiency bonus increase
    print("\nTesting level up and proficiency bonus increase:")
    print(f"Level 1: Proficiency Bonus = +{character.proficiency_bonus}")
    
    # Increase to level 5
    character.level = 5
    character.update_proficiency_bonus()
    print(f"Level 5: Proficiency Bonus = +{character.proficiency_bonus}")
    
    # Test a skill check again to see the difference
    athletics_check = make_skill_check(character, "Athletics", 15)
    print(f"\nAthletics check at level 5: {athletics_check['total']} (Roll: {athletics_check['roll']}, Modifier: {athletics_check['modifier']})")
    
    # Test saving throws
    print("\nTesting saving throws:")
    print(f"{'Saving Throw':<15} {'Proficient':<12} {'Result (DC 15)'}")
    print("-" * 50)
    
    for ability in ["STRENGTH", "DEXTERITY", "CONSTITUTION", "INTELLIGENCE", "WISDOM", "CHARISMA"]:
        # Add proficiency to STR and CON saves (Fighter's saves)
        if ability in ["STRENGTH", "CONSTITUTION"]:
            character.add_saving_throw_proficiency(ability)
        
        # Make the saving throw
        is_proficient = ability in character.saving_throw_proficiencies
        proficient_str = "Yes" if is_proficient else "No"
        
        save_result = character.make_saving_throw(ability, 15)
        success_str = "Success" if save_result["success"] else "Failure"
        result_str = f"{save_result['total']} ({success_str})"
        
        print(f"{ability.capitalize():<15} {proficient_str:<12} {result_str}")
    
    # Restore original roll function
    Dice.roll_d20 = original_roll
    
    print("\n=== SKILLS TESTING COMPLETE ===")

if __name__ == "__main__":
    test_skills()