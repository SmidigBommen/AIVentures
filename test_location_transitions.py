import unittest
import json
from GameState import GameState
from characterFactory import CharacterFactory


class TestLocationTransitions(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.gamestate = GameState()

        # Load the actual campaign data
        with open("json/campaign.json") as f:
            self.campaign = json.load(f)

        # Create a test character
        character_factory = CharacterFactory()
        self.gamestate.character = character_factory.create_character("Test Hero", "Human", "Fighter")

        # Set up initial game state using actual campaign data
        self.gamestate.act = self.campaign["acts"][0]  # Start with Act 1

        # Find the starting location
        start_location_name = self.campaign["startingLocation"]
        self.gamestate.current_location = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == start_location_name:
                self.gamestate.current_location = location
                break

    def test_act1_locations_available(self):
        """Test that Act 1 has the expected locations."""
        act1_locations = self.gamestate.act["locations"]
        location_names = [loc["name"] for loc in act1_locations]

        expected_locations = ["Rivermeet Town", "Whispering Woods", "Abandoned Watchtower"]
        for expected_loc in expected_locations:
            self.assertIn(expected_loc, location_names)

    # TODO: Add generic test for ALL locations in the act
    def test_whispering_woods_has_areas(self):
        """Test that Whispering Woods has explorable areas."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        self.assertIsNotNone(whispering_woods)
        self.assertTrue(len(whispering_woods["areas"]) > 0)
        self.assertEqual(len(whispering_woods["areas"]), 3)

        # Check that areas have required properties
        for area in whispering_woods["areas"]:
            self.assertIn("id", area)
            self.assertIn("name", area)
            self.assertIn("description", area)
            self.assertIn("connections", area)

    def test_whispering_woods_area_connections(self):
        """Test that Whispering Woods area connections are valid."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        areas = whispering_woods["areas"]

        # Create a map of area IDs for easy lookup
        area_ids = {area["id"] for area in areas}

        # Check that all connections point to valid areas
        for area in areas:
            for connection in area["connections"]:
                self.assertIn(connection, area_ids,
                              f"Area '{area['id']}' has invalid connection to '{connection}'")

    def test_whispering_woods_starting_area_exists(self):
        """Test that the starting area exists in Whispering Woods."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        starting_area_id = whispering_woods["starting_area"]

        area_ids = {area["id"] for area in whispering_woods["areas"]}
        self.assertIn(starting_area_id, area_ids,
                      f"Starting area '{starting_area_id}' not found in Whispering Woods areas")

    def test_specific_area_structure(self):
        """Test specific areas in Whispering Woods have correct structure."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        # Test entrance area
        entrance_area = None
        for area in whispering_woods["areas"]:
            if area["id"] == "entrance":
                entrance_area = area
                break

        self.assertIsNotNone(entrance_area)
        self.assertEqual(entrance_area["name"], "Forest Entrance")
        self.assertIn("clearing", entrance_area["connections"])

        # Test grove area (boss area)
        grove_area = None
        for area in whispering_woods["areas"]:
            if area["id"] == "grove":
                grove_area = area
                break

        self.assertIsNotNone(grove_area)
        self.assertEqual(grove_area["name"], "Corrupted Grove")
        self.assertIn("boss", grove_area)
        self.assertEqual(grove_area["boss"], "Shard Guardian")

    def test_bidirectional_area_connections(self):
        """Test that area connections are bidirectional - if A connects to B, then B connects to A."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        # Create a map of areas by their ID
        areas_by_id = {area["id"]: area for area in whispering_woods["areas"]}

        # Check bidirectional connections
        for area in whispering_woods["areas"]:
            for connected_area_id in area["connections"]:
                connected_area = areas_by_id[connected_area_id]

                # Check that the connected area also connects back to this area
                self.assertIn(area["id"], connected_area["connections"],
                              f"Area '{area['id']}' connects to '{connected_area_id}', "
                              f"but '{connected_area_id}' doesn't connect back to '{area['id']}'")

    def test_area_traversal_maintains_connections(self):
        """Test that when traversing from one area to another, there's always a way back."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        # Create a map of areas by their ID for easy lookup
        areas_by_id = {area["id"]: area for area in whispering_woods["areas"]}

        # Test traversal from each area to each of its connections
        for current_area in whispering_woods["areas"]:
            for next_area_id in current_area["connections"]:
                next_area = areas_by_id[next_area_id]

                # Verify that from the next area, we can get back to the current area
                self.assertIn(current_area["id"], next_area["connections"],
                              f"Cannot traverse back from '{next_area_id}' to '{current_area['id']}'")

    def test_area_graph_connectivity(self):
        """Test that all areas in a location form a connected graph (no isolated areas)."""
        # Find Whispering Woods location
        whispering_woods = None
        for location in self.gamestate.act["locations"]:
            if location["name"] == "Whispering Woods":
                whispering_woods = location
                break

        if not whispering_woods["areas"]:
            self.skipTest("No areas to test connectivity")

        # Use BFS to check if all areas are reachable from the starting area
        starting_area_id = whispering_woods["starting_area"]
        visited = set()
        queue = [starting_area_id]

        # Create areas map for quick lookup
        areas_by_id = {area["id"]: area for area in whispering_woods["areas"]}

        while queue:
            current_area_id = queue.pop(0)
            if current_area_id in visited:
                continue

            visited.add(current_area_id)
            current_area = areas_by_id[current_area_id]
            print(f"Visiting area: {current_area_id}")

            # Add all connected areas to the queue
            for connected_area_id in current_area["connections"]:
                if connected_area_id not in visited:
                    queue.append(connected_area_id)

        # Check that all areas are reachable
        all_area_ids = {area["id"] for area in whispering_woods["areas"]}
        self.assertEqual(visited, all_area_ids,
                         f"Not all areas are reachable from starting area '{starting_area_id}'. "
                         f"Reachable: {visited}, All areas: {all_area_ids}")


if __name__ == "__main__":
    unittest.main()