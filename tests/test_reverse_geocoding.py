#!/usr/bin/env python3

import unittest
import json
import sys
import os
import importlib.util

# Load the script as a module
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../bin/3-reverse-geocoding.py'))
spec = importlib.util.spec_from_file_location("reverse_geocoding", script_path)
reverse_geocoding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reverse_geocoding)

class TestReverseGeocoding(unittest.TestCase):
    
    def test_dreux_france_coordinates(self):
        """Test that the correct administrative boundaries are returned for Dreux, France."""
        # Coordinates for Dreux, France
        lat = 48.7331439
        lon = 1.3615715323474822
        
        # Get the boundaries
        boundaries_json = reverse_geocoding.get_administrative_boundaries(lat, lon)
        boundaries = json.loads(boundaries_json)
        
        # Expected boundaries for Dreux, France
        expected_boundaries = {
            "administrative_boundaries": [
                {
                    "admin_level": 2,
                    "name": "France"
                },
                {
                    "admin_level": 3,
                    "name": "France métropolitaine"
                },
                {
                    "admin_level": 4,
                    "name": "Centre-Val de Loire"
                },
                {
                    "admin_level": 6,
                    "name": "Eure-et-Loir"
                },
                {
                    "admin_level": 7,
                    "name": "Dreux"
                },
                {
                    "admin_level": 8,
                    "name": "Dreux"
                }
            ]
        }
        
        # Assert that the boundaries match the expected ones
        self.assertEqual(boundaries, expected_boundaries)
    
    def test_invalid_coordinates(self):
        """Test that empty boundaries are returned for coordinates in the middle of the ocean."""
        # Coordinates in the middle of the Atlantic Ocean
        lat = 0.0
        lon = -30.0
        
        # Get the boundaries
        boundaries_json = reverse_geocoding.get_administrative_boundaries(lat, lon)
        boundaries = json.loads(boundaries_json)
        
        # Expect empty boundaries list
        self.assertEqual(boundaries["administrative_boundaries"], [])

if __name__ == "__main__":
    unittest.main() 