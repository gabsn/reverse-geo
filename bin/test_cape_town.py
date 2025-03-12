#!/usr/bin/env python3

import json
import sys
import os

# Add the parent directory to the path so we can import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module to test
from bin.reverse_geocoding import get_administrative_boundaries

def test_cape_town_coordinates():
    """Test the coordinates for Cape Town, South Africa: -33.9331562,18.5182556"""
    # Test the coordinates
    lat, lon = -33.9331562, 18.5182556
    result_json = get_administrative_boundaries(lat, lon, debug=True)
    result = json.loads(result_json)
    
    print("\nResults for Cape Town coordinates (-33.9331562, 18.5182556):")
    print(f"Country: {result['country']}")
    print(f"Country Code: {result['countryCode']}")
    print(f"State/Province: {result['state']}")
    print(f"City: {result['city']}")
    
    return result

if __name__ == '__main__':
    test_cape_town_coordinates() 