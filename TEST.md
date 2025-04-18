# Test Plan for AIVentures

This document outlines the testing strategy for our DnD game.

## Smoke Tests

Smoke tests verify the basic functionality works correctly without diving deep into edge cases. It will help us catch any issues early on and prevent regressions.
Run these before committing code.

### Character Creation Test

The character creation test verifies:
- Characters of different races and classes can be created
- Race stat bonuses are correctly applied
- Hit die values are properly assigned by class
- Equipment can be added to inventory and equipped

### Battle System Test

The battle system test verifies:
- Initiative calculation works correctly
- Attack mechanics function properly  
- Defense actions apply bonuses
- Victory conditions are correctly detected

## Running Tests

To run all tests:
```
python3 -m unittest discover
```

To run a specific test:
```
python3 -m unittest tests.test_character_creator
```

## Future Test Areas

As development continues, we should implement tests for:

1. **Item System** - Verify items can be created, equipped, used, and have appropriate effects
2. **Level Progression** - Ensure characters gain experience and level up correctly
3. **Combat Mechanics** - Test more complex combat scenarios with multiple combatants
4. **Save/Load System** - Verify game state can be saved and loaded correctly
5. **Integration Tests** - Ensure all components work together correctly

## Test-Driven Development

For new features, consider following this test-driven development approach:
1. Write a test that defines the expected behavior
2. Run the test to verify it fails (as the feature doesn't exist yet)
3. Implement the minimum code needed to pass the test
4. Run the test to verify it passes
5. Refactor the code while ensuring tests continue to pass