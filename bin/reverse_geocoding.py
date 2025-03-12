#!/usr/bin/env python3

import sys
import json
import psycopg2
import os
import reverse_geocoder as rg
import pycountry
from psycopg2 import pool
import functools
import threading

# Initialize reverse_geocoder once at module level to avoid reloading the dataset on each call
# Set mode to 2 for faster performance (using kdtree)
rg_search = rg.RGeocoder(mode=2, verbose=False)

# Create a thread-local storage for connection pools
_thread_local = threading.local()

# Create a connection pool
def get_connection_pool():
    """Get or create a connection pool for the current thread."""
    if not hasattr(_thread_local, 'connection_pool'):
        # Adjust these to match your database credentials:
        dbname = "reverse_geo"
        dbuser = os.environ.get("USER", "gabin")  # Use system username instead of postgres
        dbpass = ""               # fill in if you require a password
        dbhost = "localhost"      # or your DB host
        dbport = 5432             # or your DB port
        
        # Create a connection pool with 5 connections per process
        _thread_local.connection_pool = pool.ThreadedConnectionPool(
            1, 5, 
            dbname=dbname,
            user=dbuser,
            password=dbpass,
            host=dbhost,
            port=dbport
        )
    return _thread_local.connection_pool

# Cache for reverse geocoding results
_geocode_cache = {}
_cache_lock = threading.Lock()

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

def determine_city(city_candidates, rg_result=None):
    """
    Determines the city name based on city candidates from different admin levels.
    
    Args:
        city_candidates: Dictionary with admin levels (7, 8, 9) as keys and city names as values
        rg_result: Optional result from reverse_geocoder to use as fallback
        
    Returns:
        The determined city name or None if no city could be determined
    """
    # Apply city selection logic: prefer level 8, then 9, then 7
    if city_candidates[8]:
        return city_candidates[8]
    elif city_candidates[9]:
        return city_candidates[9]
    elif city_candidates[7]:
        return city_candidates[7]
    
    # If no city found from admin levels and we have reverse_geocoder results
    if rg_result is not None and 'name' in rg_result:
        return rg_result['name']
    
    return None

@functools.lru_cache(maxsize=10000)
def get_administrative_boundaries_cached(lat, lon):
    """
    Cached version of get_administrative_boundaries without debug parameter.
    """
    # Round coordinates to 5 decimal places for better cache hits
    # (about 1.1 meters precision at the equator)
    lat_rounded = round(lat, 5)
    lon_rounded = round(lon, 5)
    
    # Check if we have this in our cache
    cache_key = (lat_rounded, lon_rounded)
    with _cache_lock:
        if cache_key in _geocode_cache:
            return _geocode_cache[cache_key]
    
    # Initialize result structure
    result = {
        "countryCode": None,
        "country": None,
        "state": None,
        "city": None
    }
    
    try:
        # Get a connection from the pool
        connection_pool = get_connection_pool()
        connection = connection_pool.getconn()
        
        try:
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
            cursor.execute(query, (lon_rounded, lat_rounded))
            rows = cursor.fetchall()

            cursor.close()
            
            # Track if we have admin_level 2 (country)
            has_admin_level_2 = False
            
            # Store city candidates from different admin levels
            city_candidates = {
                7: None,
                8: None,
                9: None
            }
            
            # Process database results
            for admin_level, name in rows:
                # Convert admin_level to int if it's a string
                try:
                    if admin_level is None:
                        # Skip entries with None admin_level
                        continue
                        
                    admin_level_int = int(admin_level) if isinstance(admin_level, str) else admin_level
                    
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
                except (ValueError, TypeError):
                    continue
            
            # Apply city selection logic: prefer level 8, then 9, then 7
            result["city"] = determine_city(city_candidates)
            
            # If admin_level 2 is missing or we couldn't map the country to a code,
            # use reverse_geocoder for country information
            if not has_admin_level_2 or result["countryCode"] is None:
                try:
                    # reverse_geocoder expects coordinates as (lat, lon)
                    rg_result = rg_search.query([(lat_rounded, lon_rounded)])[0]
                    
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
                    if result["city"] is None:
                        result["city"] = determine_city(city_candidates, rg_result)
                except Exception as e:
                    # If reverse_geocoder fails, just continue with what we have
                    pass
        
        finally:
            # Return the connection to the pool
            connection_pool.putconn(connection)
    
    except Exception as e:
        # If there's any error in the database query or processing,
        # we'll just return the empty result structure
        pass
    
    # Cache the result
    with _cache_lock:
        _geocode_cache[cache_key] = json.dumps(result)
    
    return json.dumps(result)

def get_administrative_boundaries(lat, lon, debug=False):
    """
    Returns a JSON string with structured administrative boundaries
    containing the point (lat, lon).
    """
    if debug:
        print(f"DEBUG: Database query for coordinates ({lat}, {lon})")
    
    # Call the cached version
    result_json = get_administrative_boundaries_cached(lat, lon)
    
    if debug:
        # Parse the result for debug output
        result = json.loads(result_json)
        print("DEBUG: Final result:")
        print(f"DEBUG:   countryCode={result['countryCode']}")
        print(f"DEBUG:   country={result['country']}")
        print(f"DEBUG:   state={result['state']}")
        print(f"DEBUG:   city={result['city']}")
    
    # Return the structured JSON with indentation if debug is enabled
    if debug:
        return json.dumps(json.loads(result_json), indent=2)
    return result_json

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Reverse geocoding script')
    parser.add_argument('latitude', type=float, help='Latitude coordinate')
    parser.add_argument('longitude', type=float, help='Longitude coordinate')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    args = parser.parse_args()

    # Get the JSON of boundaries
    boundaries_json = get_administrative_boundaries(args.latitude, args.longitude, args.debug)
    print(boundaries_json) 