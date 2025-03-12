#!/usr/bin/env python3

import sys
import json
import psycopg2
import os
import reverse_geocoder as rg
import pycountry
import argparse

# Initialize reverse_geocoder once at module level to avoid reloading the dataset on each call
# Set mode to 2 for faster performance (using kdtree)
rg_search = rg.RGeocoder(mode=2, verbose=False)

def get_country_code(country_name):
    """
    Try to find the ISO country code for a given country name using pycountry.
    Returns None if not found.
    """
    try:
        # Try direct lookup
        country = pycountry.countries.get(name=country_name)
        if country:
            return country.alpha_2
        
        # Try fuzzy search if direct lookup fails
        countries = pycountry.countries.search_fuzzy(country_name)
        if countries:
            return countries[0].alpha_2
    except (AttributeError, LookupError):
        # Handle cases where the country name isn't recognized
        pass
    
    return None

def get_administrative_boundaries(lat, lon, debug=False):
    """
    Returns a JSON string with structured administrative boundaries
    containing the point (lat, lon).
    """
    # Adjust these to match your database credentials:
    dbname = "reverse_geo"
    dbuser = os.environ.get("USER", "gabin")  # Use system username instead of postgres
    dbpass = ""               # fill in if you require a password
    dbhost = "localhost"      # or your DB host
    dbport = 5432             # or your DB port

    connection = psycopg2.connect(
        dbname=dbname,
        user=dbuser,
        password=dbpass,
        host=dbhost,
        port=dbport
    )
    cursor = connection.cursor()

    # NOTE: ST_Point(x, y) => x=lon, y=lat
    query = """
        SELECT admin_level, name
        FROM boundaries
        WHERE ST_Contains(
            geom,
            ST_SetSRID(ST_Point(%s, %s), 4326)
        )
        ORDER BY admin_level::int;
    """

    # We pass (lon, lat) since ST_Point expects (x=lon, y=lat).
    cursor.execute(query, (lon, lat))
    rows = cursor.fetchall()

    if debug:
        print(f"DEBUG: Database query for coordinates ({lat}, {lon})")
        print(f"DEBUG: Found {len(rows)} administrative boundaries")
        print("DEBUG: Raw database results:")
        for admin_level, name in rows:
            print(f"DEBUG:   admin_level={admin_level}, name={name}")

    cursor.close()
    connection.close()

    # Initialize result structure
    result = {
        "countryCode": None,
        "country": None,
        "state": None,
        "city": None
    }
    
    # Track if we have admin_level 2 (country)
    has_admin_level_2 = False
    
    # Store city candidates from different admin levels
    city_candidates = {
        7: None,
        8: None,
        9: None
    }
    
    # Store all admin levels for debug output
    all_admin_levels = {}
    
    # Process database results
    for admin_level, name in rows:
        # Convert admin_level to int if it's a string
        admin_level_int = int(admin_level) if isinstance(admin_level, str) else admin_level
        
        # Store all admin levels for debug
        all_admin_levels[admin_level_int] = name
        
        # Assign values to the appropriate fields
        if admin_level_int == 2:
            result["country"] = name
            # Try to get country code using pycountry
            result["countryCode"] = get_country_code(name)
            has_admin_level_2 = True
        elif admin_level_int == 4:
            result["state"] = name
        elif admin_level_int in [7, 8, 9]:
            city_candidates[admin_level_int] = name
    
    # Apply city selection logic: prefer level 8, then 9, then 7
    if city_candidates[8]:
        result["city"] = city_candidates[8]
    elif city_candidates[9]:
        result["city"] = city_candidates[9]
    elif city_candidates[7]:
        result["city"] = city_candidates[7]
    
    if debug:
        print("DEBUG: After processing database results:")
        print(f"DEBUG:   countryCode={result['countryCode']}")
        print(f"DEBUG:   country={result['country']}")
        print(f"DEBUG:   state={result['state']}")
        print(f"DEBUG:   city={result['city']}")
        print(f"DEBUG:   city candidates: level 7={city_candidates[7]}, level 8={city_candidates[8]}, level 9={city_candidates[9]}")
        print("DEBUG:   All admin levels found in PostgreSQL:")
        for level in sorted(all_admin_levels.keys()):
            print(f"DEBUG:     admin_level={level}, name={all_admin_levels[level]}")
    
    # If admin_level 2 is missing or we couldn't map the country to a code,
    # use reverse_geocoder for country information
    if not has_admin_level_2 or result["countryCode"] is None:
        use_reason = "Admin level 2 is missing" if not has_admin_level_2 else "Country code mapping not found"
        print(f"{use_reason}. Using reverse_geocoder for country lookup...")
        
        # reverse_geocoder expects coordinates as (lat, lon)
        rg_result = rg_search.query([(lat, lon)])[0]
        print("Raw reverse_geocoder country result:")
        print(f"Country Code: {rg_result['cc']}")
        
        if debug:
            print("DEBUG: Full reverse_geocoder result:")
            for key, value in rg_result.items():
                print(f"DEBUG:   {key}={value}")
        
        # Add the country code
        result["countryCode"] = rg_result['cc']
        
        # If we don't have a country name yet, use the one from reverse_geocoder
        if not result["country"]:
            # Try to get full country name from country code
            try:
                country = pycountry.countries.get(alpha_2=rg_result['cc'])
                if country:
                    result["country"] = country.name
                else:
                    # Fallback to just using the country code
                    result["country"] = rg_result['cc']
            except (AttributeError, LookupError):
                # Fallback to just using the country code
                result["country"] = rg_result['cc']
        
        # If city is still null, try to use the name from reverse_geocoder
        if result["city"] is None and 'name' in rg_result:
            if debug:
                print(f"DEBUG: City is null, trying to use reverse_geocoder name: {rg_result['name']}")
            result["city"] = rg_result['name']
    
    if debug:
        print("DEBUG: Final result before returning:")
        print(f"DEBUG:   countryCode={result['countryCode']}")
        print(f"DEBUG:   country={result['country']}")
        print(f"DEBUG:   state={result['state']}")
        print(f"DEBUG:   city={result['city']}")
    
    # Return the structured JSON
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Reverse geocoding script')
    parser.add_argument('latitude', type=float, help='Latitude coordinate')
    parser.add_argument('longitude', type=float, help='Longitude coordinate')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()

    # Get the JSON of boundaries
    boundaries_json = get_administrative_boundaries(args.latitude, args.longitude, args.debug)
    print(boundaries_json)