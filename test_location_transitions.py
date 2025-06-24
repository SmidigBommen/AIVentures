import unittest
import json
from GameState import GameState
from characterFactory import CharacterFactory
from main import gamestate


class TestLocationTransitions(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.gamestate = GameState()

        # Load the actual campaign data
        with open("json/campaign.json") as f:
            self.campaign = json.load(f)

        self.gamestate.campaign = self.campaign

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
        """Test that all acts with locations have areas that form a connected graph (no isolated areas)."""

        for act in self.gamestate.campaign["acts"]:
            current_act = act

            for location in current_act["locations"]:
                player_location = location

                if not player_location["areas"]:
                    self.skipTest("No areas to test connectivity")

                # Use BFS to check if all areas are reachable from the starting area
                starting_area_id = player_location["starting_area"]
                visited = set()
                queue = [starting_area_id]

                # Create areas map for quick lookup
                areas_by_id = {area["id"]: area for area in player_location["areas"]}

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
                all_area_ids = {area["id"] for area in player_location["areas"]}
                self.assertEqual(visited, all_area_ids,
                                 f"Not all areas are reachable from starting area '{starting_area_id}'. "
                                 f"Reachable: {visited}, All areas: {all_area_ids}")



if __name__ == "__main__":
    unittest.main()