#!/usr/bin/env python3

import sys
import json
import argparse
import reverse_geocoder as rg
import pycountry
from functools import lru_cache

# Initialize reverse_geocoder once at module level to avoid reloading the dataset on each call
# Set mode to 2 for faster performance (using kdtree)
rg_search = rg.RGeocoder(mode=2, verbose=False)

@lru_cache(maxsize=128)
def get_country_name(country_code):
    """
    Get the full country name from a country code.
    Uses lru_cache for efficiency when processing multiple points.
    """
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if country:
            return country.name
    except (AttributeError, LookupError):
        pass
    
    # Return the country code if we can't find the full name
    return country_code

def get_administrative_boundaries(lat, lon, debug=False):
    """
    Returns a JSON string with structured administrative boundaries
    containing the point (lat, lon) using only reverse_geocoder.
    """
    # Query the reverse geocoder (expects coordinates as (lat, lon))
    rg_result = rg_search.query([(lat, lon)])[0]
    
    if debug:
        print("DEBUG: Full reverse_geocoder result:")
        for key, value in rg_result.items():
            print(f"DEBUG:   {key}={value}")
    
    # Build the result structure
    result = {
        "countryCode": rg_result['cc'],
        "country": get_country_name(rg_result['cc']),
        "state": rg_result['admin1'],
        "city": rg_result['name']
    }
    
    if debug:
        print("DEBUG: Final result before returning:")
        print(f"DEBUG:   countryCode={result['countryCode']}")
        print(f"DEBUG:   country={result['country']}")
        print(f"DEBUG:   state={result['state']}")
        print(f"DEBUG:   city={result['city']}")
    
    # Return the structured JSON
    return json.dumps(result, indent=2)

def batch_process(coordinates, debug=False):
    """
    Process multiple coordinates in a single batch for efficiency.
    
    Args:
        coordinates: List of (lat, lon) tuples
        debug: Whether to print debug information
        
    Returns:
        List of JSON results
    """
    # Query all coordinates in a single batch
    rg_results = rg_search.query(coordinates)
    
    results = []
    for rg_result in rg_results:
        if debug:
            print(f"\nDEBUG: Processing coordinate ({rg_result['lat']}, {rg_result['lon']})")
            print("DEBUG: Reverse_geocoder result:")
            for key, value in rg_result.items():
                print(f"DEBUG:   {key}={value}")
        
        # Build the result structure
        result = {
            "countryCode": rg_result['cc'],
            "country": get_country_name(rg_result['cc']),
            "state": rg_result['admin1'],
            "city": rg_result['name']
        }
        
        if debug:
            print("DEBUG: Result:")
            print(f"DEBUG:   countryCode={result['countryCode']}")
            print(f"DEBUG:   country={result['country']}")
            print(f"DEBUG:   state={result['state']}")
            print(f"DEBUG:   city={result['city']}")
        
        results.append(json.dumps(result, indent=2))
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Efficient reverse geocoding script using only reverse_geocoder')
    parser.add_argument('latitude', type=float, help='Latitude coordinate')
    parser.add_argument('longitude', type=float, help='Longitude coordinate')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--batch', action='store_true', help='Enable batch mode (read coordinates from stdin)')
    
    args = parser.parse_args()
    
    if args.batch:
        # Batch mode: read coordinates from stdin, one per line
        print("Enter coordinates as 'latitude longitude', one per line. End with Ctrl+D (Unix) or Ctrl+Z (Windows):")
        coordinates = []
        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        lat, lon = float(parts[0]), float(parts[1])
                        coordinates.append((lat, lon))
                    except ValueError:
                        print(f"Warning: Could not parse coordinates from line: {line}", file=sys.stderr)
        except KeyboardInterrupt:
            pass
        
        if coordinates:
            results = batch_process(coordinates, args.debug)
            for i, result in enumerate(results):
                print(f"\nResult for coordinate {i+1} ({coordinates[i][0]}, {coordinates[i][1]}):")
                print(result)
        else:
            print("No valid coordinates provided.")
    else:
        # Single coordinate mode
        boundaries_json = get_administrative_boundaries(args.latitude, args.longitude, args.debug)
        print(boundaries_json) 