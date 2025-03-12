#!/usr/bin/env python3

import unittest
import json
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from bin.reverse_geocoding import determine_city, get_administrative_boundaries

class TestReverseGeocoding(unittest.TestCase):
    
    def test_determine_city_with_admin_level_8(self):
        """Test city determination when admin level 8 is present"""
        city_candidates = {7: "City Level 7", 8: "City Level 8", 9: "City Level 9"}
        self.assertEqual(determine_city(city_candidates), "City Level 8")
    
    def test_determine_city_with_admin_level_9(self):
        """Test city determination when admin level 9 is present but 8 is missing"""
        city_candidates = {7: "City Level 7", 8: None, 9: "City Level 9"}
        self.assertEqual(determine_city(city_candidates), "City Level 9")
    
    def test_determine_city_with_admin_level_7(self):
        """Test city determination when only admin level 7 is present"""
        city_candidates = {7: "City Level 7", 8: None, 9: None}
        self.assertEqual(determine_city(city_candidates), "City Level 7")
    
    def test_determine_city_with_rg_fallback(self):
        """Test city determination with reverse_geocoder fallback"""
        city_candidates = {7: None, 8: None, 9: None}
        rg_result = {'name': 'RG City'}
        self.assertEqual(determine_city(city_candidates, rg_result), "RG City")
    
    def test_determine_city_no_city_found(self):
        """Test city determination when no city can be found"""
        city_candidates = {7: None, 8: None, 9: None}
        self.assertIsNone(determine_city(city_candidates))
    
    @patch('bin.reverse_geocoding.get_connection_pool')
    def test_cape_town_coordinates(self, mock_get_connection_pool):
        """Test the coordinates for Cape Town, South Africa: -33.9331562,18.5182556"""
        # Mock the database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock the connection pool
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_get_connection_pool.return_value = mock_pool
        
        # Mock the database query results for Cape Town
        # These are example admin levels that might be returned for Cape Town
        mock_cursor.fetchall.return_value = [
            ('2', 'South Africa'),  # Country
            ('4', 'Western Cape'),  # Province/State
            ('8', 'Cape Town')      # City
        ]
        
        # Test the coordinates
        lat, lon = -33.9331562, 18.5182556
        result_json = get_administrative_boundaries(lat, lon)
        result = json.loads(result_json)
        
        # Verify the results
        self.assertEqual(result['country'], 'South Africa')
        self.assertEqual(result['countryCode'], 'ZA')
        self.assertEqual(result['state'], 'Western Cape')
        self.assertEqual(result['city'], 'Cape Town')
        
        # Verify that the determine_city function was used correctly
        city_candidates = {7: None, 8: 'Cape Town', 9: None}
        self.assertEqual(determine_city(city_candidates), 'Cape Town')

if __name__ == '__main__':
    unittest.main() 