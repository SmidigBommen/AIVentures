# Test Suite

Run all tests with:

```bash
python3 -m pytest test/ -v
```

---

## test/test_battle.py

Battle system smoke tests using a Human Fighter vs a Goblin Ranger (Shortbow).

| Test | Description |
|------|-------------|
| `test_initiative_calculation` | Verifies initiative rolls return two entries (player and monster) with correct names. |
| `test_attack_mechanics` | Mocks d20 to always roll 20, then checks that both player and monster attacks hit and deal positive damage. |
| `test_defense_mechanics` | Checks that player and monster defend actions return a "defend" action with a positive AC bonus. |
| `test_victory_detection` | Verifies `check_victory()` returns `None` when both alive, monster name when player dies, and player name when monster dies. |

---

## test/test_character_creator.py

Character creation smoke tests covering race bonuses, hit dice, and weapon equipping.

| Test | Description |
|------|-------------|
| `test_character_creation` | Creates a Human Fighter, Elf Wizard, and Dwarf Cleric. Verifies race stat bonuses are applied correctly (Human STR 11, Elf DEX 12, Dwarf CON 12), hit dice match class (Fighter d10, Wizard d6, Cleric d8), and equipping a Longsword sets the main hand slot. |

---

## test/test_monster_encounters.py

Data integrity tests that validate monster JSON files against the weapon catalog and campaign data.

| Test | Description |
|------|-------------|
| `test_all_races_have_required_fields` | Every race in `monster_default_values.json` has all required fields (stats, base_ac, hit_die, weapons, class_options, names, challenge_rating). |
| `test_weapons_reference_valid_catalog_entries` | Every weapon listed in a monster race's `weapons` array exists in `weapon-catalog.json`. |
| `test_names_are_nonempty` | Every monster race has at least one name. |
| `test_class_options_are_nonempty` | Every monster race has at least one class option. |
| `test_campaign_monster_types_exist_in_defaults` | Every `monster_types` entry in campaign areas references a race that exists in `monster_default_values.json`. |
| `test_areas_with_encounters_have_monster_types` | Every campaign area with `encounters > 0` has a `monster_types` list defined. |
| `test_hp_calculation_works_for_every_race` | Creates every monster race at levels 1, 5, and 10 via `MonsterFactory` and verifies HP >= 1. |
| `test_challenge_rating_is_positive_integer` | Every monster race has a `challenge_rating` that is a positive integer. |
| `test_hit_die_is_valid` | Every monster race uses a valid die size (d4, d6, d8, d10, d12, or d20). |

---

## test/test_skills.py

End-to-end skills system test covering skill checks, proficiency bonuses, and saving throws.

| Test | Description |
|------|-------------|
| `test_skills` | Creates a Human Fighter, adds proficiencies (Athletics, Intimidation, Perception), mocks d20 to roll 10, then verifies skill modifiers and DC 15 checks for all skills. Levels up to 5, confirms proficiency bonus increases, and tests all six saving throws (with STR/CON proficiency). |

---

## Last Run Results

```
$ python3 -m pytest test/ -v

test/test_battle.py::BattleSmokeTest::test_attack_mechanics           PASSED
test/test_battle.py::BattleSmokeTest::test_defense_mechanics           PASSED
test/test_battle.py::BattleSmokeTest::test_initiative_calculation      PASSED
test/test_battle.py::BattleSmokeTest::test_victory_detection           PASSED
test/test_character_creator.py::CharacterCreationSmokeTest::test_character_creation  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_all_races_have_required_fields  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_weapons_reference_valid_catalog_entries  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_names_are_nonempty  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_class_options_are_nonempty  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_campaign_monster_types_exist_in_defaults  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_areas_with_encounters_have_monster_types  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_hp_calculation_works_for_every_race  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_challenge_rating_is_positive_integer  PASSED
test/test_monster_encounters.py::TestMonsterDataIntegrity::test_hit_die_is_valid  PASSED
test/test_skills.py::test_skills                                       PASSED

15 passed in 0.02s
```

**Date**: 2026-02-06
