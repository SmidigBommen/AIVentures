"""Tests for campaign area graph integrity — connections, reachability, bidirectionality."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _load_campaign():
    with open(Path(__file__).parent.parent / "json" / "campaign.json") as f:
        return json.load(f)


class TestBidirectionalConnections:
    def test_all_area_connections_are_bidirectional(self):
        """If area A connects to B, then B must connect back to A."""
        campaign = _load_campaign()
        for act in campaign["acts"]:
            for location in act["locations"]:
                areas_by_id = {area["id"]: area for area in location["areas"]}
                for area in location["areas"]:
                    for conn_id in area["connections"]:
                        connected = areas_by_id[conn_id]
                        assert area["id"] in connected["connections"], (
                            f"Area '{area['id']}' connects to '{conn_id}', "
                            f"but '{conn_id}' doesn't connect back "
                            f"(in {location['name']}, Act {act['number']})")


class TestAreaGraphConnectivity:
    def test_all_areas_reachable_from_start(self):
        """BFS from starting_area must reach every area in each location."""
        campaign = _load_campaign()
        for act in campaign["acts"]:
            for location in act["locations"]:
                if not location["areas"]:
                    continue
                starting_area_id = location["starting_area"]
                areas_by_id = {area["id"]: area for area in location["areas"]}

                # BFS
                visited = set()
                queue = [starting_area_id]
                while queue:
                    current_id = queue.pop(0)
                    if current_id in visited:
                        continue
                    visited.add(current_id)
                    for conn_id in areas_by_id[current_id]["connections"]:
                        if conn_id not in visited:
                            queue.append(conn_id)

                all_ids = set(areas_by_id.keys())
                assert visited == all_ids, (
                    f"Not all areas reachable from '{starting_area_id}' "
                    f"in {location['name']}, Act {act['number']}. "
                    f"Unreachable: {all_ids - visited}")


class TestAreaDataIntegrity:
    def test_connections_reference_valid_areas(self):
        """Every connection ID must reference an area that actually exists."""
        campaign = _load_campaign()
        for act in campaign["acts"]:
            for location in act["locations"]:
                valid_ids = {area["id"] for area in location["areas"]}
                for area in location["areas"]:
                    for conn_id in area["connections"]:
                        assert conn_id in valid_ids, (
                            f"Area '{area['id']}' references connection '{conn_id}' "
                            f"which doesn't exist in {location['name']}")

    def test_starting_area_exists(self):
        """Each location's starting_area must be a valid area ID."""
        campaign = _load_campaign()
        for act in campaign["acts"]:
            for location in act["locations"]:
                valid_ids = {area["id"] for area in location["areas"]}
                assert location["starting_area"] in valid_ids, (
                    f"starting_area '{location['starting_area']}' not found "
                    f"in {location['name']}, Act {act['number']}")

    def test_no_self_connections(self):
        """An area should not connect to itself."""
        campaign = _load_campaign()
        for act in campaign["acts"]:
            for location in act["locations"]:
                for area in location["areas"]:
                    assert area["id"] not in area["connections"], (
                        f"Area '{area['id']}' has a self-connection "
                        f"in {location['name']}")
